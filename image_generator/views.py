import threading
import asyncio # asyncio를 사용하기 위해 임포트
import uuid
import base64 # Base64 인코딩을 위해 임포트
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.cache import cache
from django.conf import settings
from django.core.files.storage import default_storage # FileSystemStorage 대신 default_storage 사용
from django.shortcuts import render
from .models import GeneratedImage, Conversation, Message # Conversation, Message 모델 임포트 추가
from django.db.models import Q # Q 객체 import (검색 필터링에 사용)
from collections import defaultdict
from django.utils import timezone # timezone.now()를 사용하기 위해 임포트
import os
import json
import time
import httpx # httpx는 image_logic_parser.py에서 사용되지만, 여기에 import 되어 있어 유지합니다.
import random
import traceback
import logging
from asgiref.sync import sync_to_async # [추가] 동기 함수를 비동기 컨텍스트에서 실행하기 위함


from llm_cores.translation_service import translate_text
from llm_cores.gemma_service import get_docent_response # Gemma 서비스 임포트

from .image_logic_parser import generate_image_based_on_json_logic
from llm_cores.positive_prompts import POSITIVE_PROMPT_MAP
from llm_cores.negative_prompts import NEGATIVE_PROMPT_MAP


logger = logging.getLogger(__name__)

# ComfyUI 관련 설정
COMFYUI_API_URL = getattr(settings, 'COMFYUI_API_URL', 'http://localhost:8188')
COMFYUI_HISTORY_URL = getattr(settings, 'COMFYUI_HISTORY_URL', 'http://localhost:8188/history')
COMFYUI_IMAGE_URL = getattr(settings, 'COMFYUI_IMAGE_URL', 'http://localhost:8188/view')
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', os.path.join(settings.MEDIA_ROOT, 'comfyui_input'))


# --- HTML 페이지 뷰 함수들 (urls.py에 명시된 대로 복원) ---
def welcome_view(request):
    """웰컴 페이지를 렌더링합니다."""
    return render(request, 'welcome.html')

def features_view(request):
    """기능 소개 페이지를 렌더링합니다."""
    return render(request, 'features.html')

def about_view(request):
    """소개 페이지를 렌더링합니다."""
    return render(request, 'about.html')

def main_view(request):
    """메인 페이지 (챗봇 및 이미지 생성 인터페이스)를 렌더링합니다."""
    return render(request, 'main.html') # 기존 index.html 사용

# 전시관 데이터를 로드하는 함수
def load_museum_data():
    file_path = os.path.join(settings.BASE_DIR, 'gallery_data', 'cleaned_museum_data.json')
    
    logger.info(f"DEBUG: Attempting to load museum data from: {file_path}")
    
    # [수정] 도시 이름 표준화를 위한 매핑 강화
    # JSON 파일의 'address' 필드에서 시/도 이름을 추출하고 표준화합니다.
    city_name_mapping = {
        "서울": "서울특별시", "서울특별시": "서울특별시",
        "경기": "경기도", "경기도": "경기도",
        "부산": "부산광역시", "부산광역시": "부산광역시",
        "대구": "대구광역시", "대구광역시": "대구광역시",
        "인천": "인천광역시", "인천광역시": "인천광역시",
        "광주": "광주광역시", "광주광역시": "광주광역시",
        "대전": "대전광역시", "대전광역시": "대전광역시",
        "울산": "울산광역시", "울산광역시": "울산광역시",
        "세종": "세종특별자치시", "세종특별자치시": "세종특별자치시",
        "강원": "강원특별자치도", "강원특별자치도": "강원특별자치도", # 강원특별자치도 추가
        "충북": "충청북도", "충청북도": "충청북도",
        "충남": "충청남도", "충청남도": "충청남도",
        "전북": "전라북도", "전라북도": "전라북도", # 전북특별자치도 추가
        "전남": "전라남도", "전라남도": "전라남도",
        "경북": "경상북도", "경상북도": "경상북도",
        "경남": "경상남도", "경상남도": "경상남도",
        "제주": "제주특별자치도", "제주특별자치도": "제주특별자치도",
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        valid_museums = []
        for museum in data:
            # 주소에서 시/도 정보 추출 및 표준화
            address = museum.get('address', '')
            found_city = None
            for key, value in city_name_mapping.items():
                # 주소가 매핑 키로 시작하는지 확인 (가장 긴 매핑부터 확인하는 것이 더 정확할 수 있음)
                if address.startswith(key):
                    found_city = value
                    break
            
            # 'city' 필드가 없거나, 추출된 도시 정보가 없는 경우 추가
            # 기존 'city' 필드가 있다면 덮어쓰거나, 없으면 새로 추가
            museum['city'] = found_city if found_city else "기타" # 매핑된 도시가 없으면 '기타'로 분류
            
            # 위도, 경도 유효성 검사 (기존 로직 유지)
            if 'latitude' in museum and museum['latitude'] is not None and \
               'longitude' in museum and museum['longitude'] is not None and \
               isinstance(museum['latitude'], (int, float)) and \
               isinstance(museum['longitude'], (int, float)):
                valid_museums.append(museum)
            else:
                logger.warning(f"Skipping museum due to invalid lat/lon: {museum.get('name', 'Unknown')}")
        
        # 도시별로 그룹화 (기존 로직 유지)
        museums_by_city = defaultdict(list)
        for museum in valid_museums:
            city = museum.get('city', '기타') # city 필드가 없으면 '기타'로 분류
            museums_by_city[city].append(museum)
        
        return museums_by_city

    except FileNotFoundError:
        logger.error(f"Error: cleaned_museum_data.json not found at {file_path}")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON from {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading museum data: {e}", exc_info=True)
        return {}

# 전시관 목록 페이지 뷰
def gallery_view(request):
    museums_by_city = load_museum_data()
    
    # [수정] 모든 박물관 데이터를 단일 리스트로 변환
    all_museums = []
    for city_list in museums_by_city.values():
        all_museums.extend(city_list)

    # JsonResponse로 반환할 때 ensure_ascii=False를 사용하여 한글 깨짐 방지
    museum_data_json = json.dumps(all_museums, ensure_ascii=False) # all_museums를 JSON으로 덤프
    
    logger.info(f"DEBUG: museum_data_json to be passed to template (first 200 chars): {museum_data_json[:200]}...")
    
    context = {
        'museum_data': museum_data_json, # 템플릿으로 JSON 문자열 전달
    }
    return render(request, 'gallery.html', context)


def archive_view(request):
    """아카이브 페이지를 렌더링합니다."""
    return render(request, 'archive.html')

# --- API 엔드포인트 (urls.py에 명시된 이름으로 변경 및 기존 로직 유지) ---

# 대화 기록 가져오기 API (이전 api_get_conversations)
@csrf_exempt
@require_GET
async def get_conversations_api(request): # [수정] async def로 변경
    limit = int(request.GET.get('limit', 5)) # 기본 5개
    offset = int(request.GET.get('offset', 0)) # 기본 0부터 시작

    # [수정] 쿼리셋을 리스트로 변환하고 await
    all_conversations = await sync_to_async(list)(Conversation.objects.order_by('-created_at'))
    # [수정] count()도 await sync_to_async
    total_count = await sync_to_async(Conversation.objects.count)() 

    conversation_list = []
    # 개별 대화 처리 시 예외 처리 추가
    for conv in all_conversations[offset:offset + limit]:
        try:
            # [수정] related_name을 통한 메시지 접근도 sync_to_async로 래핑하고 await
            last_message = await sync_to_async(conv.messages.order_by('-timestamp').first)()
            preview_text = last_message.text if last_message else "대화 내용 없음"
            
            first_message = await sync_to_async(conv.messages.order_by('timestamp').first)()
            first_message_text = first_message.text if first_message else ""

            conversation_list.append({
                'id': str(conv.id), # Django 모델의 기본 ID 필드
                'session_id': str(conv.session_id), # UUID 필드
                # [수정] Conversation 모델에는 'title' 필드가 없으므로 'summary' 필드를 사용합니다.
                # summary가 비어있으면 첫 메시지 50자를 사용
                'title': conv.summary if conv.summary else first_message_text[:50], # 요약 또는 첫 메시지 50자
                'preview': preview_text,
                'created_at': conv.created_at.isoformat()
            })
        except Exception as e:
            # 특정 대화 처리 중 오류 발생 시 로그 기록 및 해당 대화 건너뛰기
            logger.error(f"Error processing conversation {conv.session_id} (ID: {conv.id}) for listing: {e}", exc_info=True)
            continue # 오류가 발생한 대화는 목록에 추가하지 않고 다음 대화로 넘어갑니다.

    return JsonResponse({'conversations': conversation_list, 'total_count': total_count})

# 특정 대화의 메시지 가져오기 API (이전 api_get_messages)
@csrf_exempt
@require_GET
async def get_conversation_history_api(request, conversation_id): # [수정] async def로 변경
    try:
        conversation = await sync_to_async(Conversation.objects.get)(session_id=conversation_id)
        # [수정] Message 모델은 created_at 대신 timestamp 필드를 사용합니다.
        messages_queryset = Message.objects.filter(conversation=conversation).order_by('timestamp')
        message_list = []
        # [수정] 메시지 순회도 비동기 컨텍스트에서 안전하게
        for msg in await sync_to_async(list)(messages_queryset): # 쿼리셋을 리스트로 변환하여 순회
            message_data = {
                'sender': msg.sender,
                'text': msg.text,
                'created_at': msg.timestamp.isoformat() # [수정] timestamp 필드 사용
            }
            # Message 모델에 image 필드가 아닌 image_url 필드가 있으므로 수정
            if msg.image_url:
                message_data['image_url'] = msg.image_url
            message_list.append(message_data)
        return JsonResponse({'status': 'success', 'history': message_list}) # 'messages'를 'history'로 변경
    except Conversation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '대화를 찾을 수 없습니다.'}, status=404)

# 오래된 대화 정리 API (urls.py에 명시되지 않았지만 기존 로직 유지를 위해 포함)
@csrf_exempt
@require_POST
async def api_cleanup_conversations(request): # [수정] async def로 변경
    # 30일보다 오래된 대화를 삭제
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    # [수정] filter 쿼리셋을 먼저 생성하고, count와 delete를 sync_to_async로 래핑하여 await
    old_conversations_queryset = Conversation.objects.filter(created_at__lt=thirty_days_ago)
    count_deleted = await sync_to_async(old_conversations_queryset.count)()
    await sync_to_async(old_conversations_queryset.delete)()
    return JsonResponse({'status': 'success', 'message': f'{count_deleted}개의 오래된 대화가 삭제되었습니다.'})

# 최대 대화 개수 초과 시 오래된 대화 삭제 API (이전 api_delete_oldest_conversations)
@csrf_exempt
@require_POST
async def delete_oldest_conversations_api(request): # [수정] async def로 변경
    # [수정] request.POST에서 'count' 파라미터 가져오기
    count_to_delete = int(request.POST.get('count', 0)) 

    if count_to_delete <= 0:
        return JsonResponse({'status': 'success', 'message': '삭제할 대화 개수가 지정되지 않았습니다.'})

    # [수정] all().order_by() 호출 결과를 먼저 await하고 슬라이싱
    oldest_conversations_queryset = Conversation.objects.all().order_by('created_at')
    # 쿼리셋 슬라이싱은 동기적으로 가능하므로, 리스트로 변환하는 시점에 await
    oldest_conversations_list = await sync_to_async(list)(oldest_conversations_queryset[:count_to_delete])

    deleted_count = 0
    # [수정] 순회도 비동기 컨텍스트에서 안전하게
    for conv in oldest_conversations_list: # 리스트를 순회
        await sync_to_async(conv.delete)() # [수정] delete()도 sync_to_async
        deleted_count += 1
    
    return JsonResponse({'status': 'success', 'message': f'{deleted_count}개의 오래된 대화가 삭제되었습니다.'})


# 이미지 갤러리 API (이름 유지)
@csrf_exempt
@require_GET
async def api_get_images(request): # [수정] async def로 변경
    search_query = request.GET.get('search', '')
    selected_style = request.GET.get('style', '')
    sort_order = request.GET.get('sort', 'latest')

    # [수정] filter 쿼리셋을 먼저 생성
    images_queryset = GeneratedImage.objects.filter(is_showcase=True)

    if search_query:
        # [수정] filter도 sync_to_async로 래핑하여 await
        images_queryset = await sync_to_async(images_queryset.filter)(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(prompt__icontains=search_query)
        )
    
    if selected_style:
        # [수정] filter도 sync_to_async로 래핑하여 await
        images_queryset = await sync_to_async(images_queryset.filter)(style=selected_style)

    if sort_order == 'latest':
        # [수정] order_by도 sync_to_async로 래핑하여 await
        images_queryset = await sync_to_async(images_queryset.order_by)('-created_at')
    elif sort_order == 'popular':
        # 'popular' 정렬을 위한 로직 (예: view_count가 높은 순)
        # GeneratedImage 모델에 view_count 필드가 없으므로 views 필드를 사용합니다.
        # [수정] order_by도 sync_to_async로 래핑하여 await
        images_queryset = await sync_to_async(images_queryset.order_by)('-views') 
    elif sort_order == 'oldest':
        # [수정] order_by도 sync_to_async로 래핑하여 await
        images_queryset = await sync_to_async(images_queryset.order_by)('created_at')

    image_list = []
    # [수정] 순회도 비동기 컨텍스트에서 안전하게
    for img in await sync_to_async(list)(images_queryset): # 쿼리셋을 리스트로 변환하여 순회
        image_list.append({
            'id': str(img.id),
            # GeneratedImage 모델에 image 필드가 아닌 image_file 필드가 있으므로 수정
            # [수정] url 속성 접근도 sync_to_async (람다 사용)
            'url': await sync_to_async(lambda: img.image_file.url)(), 
            'title': img.title,
            'description': img.description,
            'prompt': img.prompt,
            'style': img.style,
            'created_at': img.created_at.isoformat(),
            # GeneratedImage 모델에 view_count 필드가 없으므로 views 필드를 사용합니다.
            'view_count': img.views
        })
    return JsonResponse({'images': image_list})

# extract_categories_from_text 함수
def extract_categories_from_text(text: str) -> tuple[list, list]:
    """
    텍스트에서 llm_cores/positive_prompts.py 및 negative_prompts.py에 정의된
    프롬프트 맵의 키(카테고리)를 기반으로 긍정 및 부정 프롬프트 카테고리를 추출합니다.
    """
    found_positive_categories = set()
    found_negative_categories = set()

    lower_text = text.lower()

    for category_key in POSITIVE_PROMPT_MAP.keys():
        if category_key.lower() in lower_text:
            found_positive_categories.add(category_key)
    
    for category_key in NEGATIVE_PROMPT_MAP.keys():
        if category_key.lower() in lower_text:
            found_negative_categories.add(category_key)
            
    return list(found_positive_categories), list(found_negative_categories)


# 이미지 생성 API (이전 api_generate_image -> process_request_api로 이름 변경)
@csrf_exempt
@require_POST
async def process_request_api(request): # [수정] async def로 변경
    logger.info("process_request_api called.")
    try:
        # [수정] JSON 바디를 직접 파싱하도록 변경
        data = json.loads(request.body)
        user_message = data.get('user_message', '').strip()
        user_image_data_base64 = data.get('image_data', None) # Base64 문자열 (Data URL 포함 가능)
        conversation_id = data.get('conversation_id')
        current_mode = data.get('current_mode', 'curator')

        logger.info(f"Received request: Mode='{current_mode}', Conversation ID='{conversation_id}', User message='{user_message[:50]}'")
        if user_image_data_base64:
            logger.info(f"Received image data (first 50 chars): {user_image_data_base64[:50]}...")
        else:
            logger.info("No image data received.")

        # 새 대화이거나 기존 대화 ID가 유효하지 않으면 새 대화 생성
        # [수정] sync_to_async 사용 방식 변경: exists() 메서드를 호출하는 부분까지 래핑
        if conversation_id == 'new-chat' or not await sync_to_async(Conversation.objects.filter(session_id=conversation_id).exists)():
            summary_text = user_message[:50] if user_message else "새 대화"
            # [수정] create() 메서드를 sync_to_async로 래핑
            conversation = await sync_to_async(Conversation.objects.create)(summary=summary_text, start_time=timezone.now())
            conversation_id = str(conversation.session_id)
            logger.info(f"New conversation created with ID: {conversation_id}")
        else:
            # [수정] get() 메서드를 sync_to_async로 래핑
            conversation = await sync_to_async(Conversation.objects.get)(session_id=conversation_id)
            logger.info(f"Continuing conversation with ID: {conversation_id}")

        # 사용자 메시지 저장
        # [수정] create() 메서드를 sync_to_async로 래핑
        await sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender='user',
            text=user_message,
            timestamp=timezone.now()
        )

        response_text = ""
        image_url = None
        image_file_path = None # 내부 저장 경로

        # 강화된 Base64 데이터 클리닝 로직
        cleaned_image_data_for_ollama = None
        if isinstance(user_image_data_base64, str) and user_image_data_base64.strip() and \
           user_image_data_base64.strip().lower() not in ['null', 'undefined']:
            if "," in user_image_data_base64:
                cleaned_image_data_for_ollama = user_image_data_base64.split(',')[1]
                logger.info("Data URL prefix removed from image data for Ollama.")
            else:
                cleaned_image_data_for_ollama = user_image_data_base64
                logger.info("No Data URL prefix found, using image data as is for Ollama.")
            
            try:
                # Base64 디코딩 시 유효성 검사 (실제 데이터가 아닌 경우 오류 방지)
                base64.b64decode(cleaned_image_data_for_ollama, validate=True)
                logger.info("Cleaned image data for Ollama is valid Base64.")
            except Exception as e:
                logger.error(f"Cleaned image data for Ollama is NOT valid Base64: {e}. Data (first 50 chars): {cleaned_image_data_for_ollama[:50]}", exc_info=True)
                cleaned_image_data_for_ollama = None 
        else:
            logger.info("User image data was null, empty, or an invalid string representation of null/undefined. Not passing to Ollama.")


        if current_mode == 'curator':
            # --- 도슨트 모드 처리 ---
            # [수정] get_docent_response는 동기 함수이므로 sync_to_async로 래핑하고 await
            docent_response = await sync_to_async(get_docent_response)(user_message, cleaned_image_data_for_ollama)
            response_text = docent_response
            # --------------------------

        elif current_mode == 'image_generation':
            # --- 이미지 생성 모드 처리 ---
            try:
                temp_image_file_path = None
                if cleaned_image_data_for_ollama: # Base64 데이터가 있을 경우
                    try:
                        image_bytes = base64.b64decode(cleaned_image_data_for_ollama)
                        temp_file_name = f"temp_upload_{uuid.uuid4()}.jpg" 
                        temp_image_file_path = os.path.join(settings.MEDIA_ROOT, 'temp_uploads', temp_file_name)
                        
                        # [수정] os.makedirs도 sync_to_async로 래핑
                        await sync_to_async(os.makedirs)(os.path.dirname(temp_image_file_path), exist_ok=True)

                        # [수정] default_storage.save를 사용하여 ContentFile로 저장
                        saved_file_name = await sync_to_async(default_storage.save)(temp_image_file_path, ContentFile(image_bytes))
                        temp_image_file_path = saved_file_name # 저장된 실제 경로로 업데이트
                        logger.info(f"Temporary image saved for image generation: {temp_image_file_path}")
                    except Exception as e:
                        logger.error(f"Error saving temporary image for image generation: {e}", exc_info=True)
                        temp_image_file_path = None

                image_gen_result = await generate_image_based_on_json_logic(
                    user_input=user_message,
                    uploaded_image_path=temp_image_file_path, # 저장된 임시 파일 경로 전달
                    mode=current_mode, 
                    positive_categories=extract_categories_from_text(user_message)[0],
                    negative_categories=extract_categories_from_text(user_message)[1]
                )
                # [수정] default_storage.url도 sync_to_async로 래핑
                image_url = await sync_to_async(default_storage.url)(image_gen_result['image_file_path'])
                image_file_path = image_gen_result['image_file_path']
                response_text = "이미지가 성공적으로 생성되었습니다!"

            except Exception as e:
                logger.error(f"Error during image generation: {e}", exc_info=True)
                response_text = f"이미지 생성 중 오류가 발생했습니다: {e}"
                image_url = None
            finally:
                # [수정] default_storage.exists와 default_storage.delete도 sync_to_async로 래핑
                if temp_image_file_path and await sync_to_async(default_storage.exists)(temp_image_file_path):
                    try:
                        await sync_to_async(default_storage.delete)(temp_image_file_path)
                        logger.info(f"Temporary image deleted: {temp_image_file_path}")
                    except Exception as e:
                        logger.warning(f"Error deleting temporary image {temp_image_file_path}: {e}")

            # ---------------------------

        # 챗봇 응답 저장
        # [수정] create() 메서드를 sync_to_async로 래핑
        await sync_to_async(Message.objects.create)(
            conversation=conversation,
            sender='bot',
            text=response_text,
            image_file_path=image_file_path,
            image_url=image_url,
            timestamp=timezone.now()
        )

        return JsonResponse({
            'status': 'success',
            'response': response_text,
            'image_url': image_url,
            'conversation_id': conversation_id
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON received in process_request_api", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.critical(f"Unexpected error in process_request_api: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


# 이미지 생성 작업 상태 확인 API
@csrf_exempt
@require_GET
async def check_task_status_api(request, task_id): # [수정] async def로 변경
    """
    비동기 이미지 생성 작업의 상태를 캐시에서 조회하여 반환합니다.
    프론트엔드에서 이 API를 주기적으로 폴링하여 작업 완료 여부를 확인합니다.
    """
    # [수정] cache.get도 sync_to_async로 래핑
    status_data = await sync_to_async(cache.get)(f"task_status_{task_id}")
    if status_data:
        logger.info(f"Task status request for {task_id}: {status_data.get('status')}")
        return JsonResponse(status_data)
    else:
        # [추가] 캐시에 작업 상태가 없는 경우 (아직 처리 중이거나 만료된 경우)
        # PENDING 상태로 간주하고 메시지를 반환합니다.
        logger.warning(f"Task {task_id} not found in cache. Assuming PENDING status.")
        return JsonResponse({
            'status': 'PENDING',
            'message': '작업이 처리 중이거나 큐에서 대기 중입니다.',
            'image_url': None # 아직 이미지가 없습니다.
        }, status=200)


# 이미지 생성 완료 처리 내부 함수 (비동기)
async def _generate_image_task_runner(task_id, conversation_id, original_prompt, uploaded_image_path, current_mode, positive_categories, negative_categories): # [수정] uploaded_image_file -> uploaded_image_path
    """
    실제 이미지 생성 로직을 비동기적으로 실행하고 결과를 캐시에 저장합니다.
    이 함수는 별도의 스레드에서 실행됩니다.
    """
    image_url = None
    status = "FAILED"
    message_for_frontend = "이미지 생성 중 알 수 없는 오류가 발생했습니다."

    try:
        if current_mode == 'image_generation':
            try:
                result = await generate_image_based_on_json_logic(
                    user_input=original_prompt, 
                    uploaded_image_path=uploaded_image_path, # [수정] 파일 객체 대신 경로 전달
                    mode=current_mode, 
                    positive_categories=positive_categories, 
                    negative_categories=negative_categories
                )
                # [수정] default_storage.url도 sync_to_async로 래핑
                image_url = await sync_to_async(default_storage.url)(result['image_file_path']) # 저장된 이미지의 URL 가져오기
                status = "COMPLETED"
                message_for_frontend = "이미지 생성이 완료되었습니다!"
            except Exception as e:
                message_for_frontend = f"이미지 생성 서비스에서 오류가 발생했습니다: {str(e)}"
                status = "FAILED"
                logger.error(f"Error during image generation for task {task_id}: {e}", exc_info=True)
        else:
            message_for_frontend = "현재 모드에서는 이미지 생성을 지원하지 않습니다."
            status = "FAILED"

    except Exception as e:
        message_for_frontend = f"이미지 생성 중 심각한 오류가 발생했습니다: {str(e)}"
        status = "FAILED"
        logger.error(f"Error in _generate_image_task_runner for task {task_id}: {e}", exc_info=True)
    finally:
        # [수정] cache.set도 sync_to_async로 래핑
        await sync_to_async(cache.set)(f"task_status_{task_id}", {
            "status": status,
            "image_url": image_url,
            "message": message_for_frontend,
            "conversation_id": conversation_id,
            "original_prompt": original_prompt,
            "style": "default"
        }, timeout=300)

        await _handle_image_generation_completion(task_id, status, image_url, message_for_frontend, conversation_id, original_prompt, "default")


async def _handle_image_generation_completion(task_id, status, image_url, message_from_task, conversation_id, original_prompt, style):
    logger.info(f"Callback handler for Task {task_id}: Status {status}, Image URL {image_url}, Message: {message_from_task}")
    try:
        # [수정] Conversation.objects.get을 sync_to_async로 래핑
        conversation = await sync_to_async(Conversation.objects.get)(session_id=conversation_id)

        if status == 'COMPLETED' and image_url:
            if not image_url.startswith(settings.MEDIA_URL) and not image_url.startswith('http'):
                image_url = os.path.join(settings.MEDIA_URL, image_url.lstrip('/'))
            
            ai_response_text = message_from_task
            # [수정] Message.objects.create를 sync_to_async로 래핑
            await sync_to_async(Message.objects.create)(
                conversation=conversation,
                sender='ai',
                text=ai_response_text,
                image_url=image_url
            )
            logger.info(f"Conversation {conversation_id} updated with image URL: {image_url}")

        elif status == 'FAILED':
            ai_response_text = message_from_task
            # [수정] Message.objects.create를 sync_to_async로 래핑
            await sync_to_async(Message.objects.create)(
                conversation=conversation,
                sender='ai',
                text=ai_response_text
            )
            logger.error(f"Image generation failed for Task {task_id}: {message_from_task}")
        else:
            logger.warning(f"Callback handler for Task {task_id}: Unknown status received: {status}")

    except Conversation.DoesNotExist:
        logger.error(f"Callback handler for Task {task_id}: Conversation {conversation_id} not found.")
    except Exception as e:
        logger.error(f"Callback handler for Task {task_id}: Error processing completion: {e}", exc_info=True)


@csrf_exempt
@require_POST
def api_image_generation_callback(request):
    try:
        data = json.loads(request.body)
        task_id = data.get('task_id')
        status = data.get('status')
        image_url = data.get('image_url')
        message_from_callback = data.get('message') 
        conversation_id = data.get('conversation_id')
        original_prompt = data.get('original_prompt')
        style = data.get('style', 'Fantasy')

        # asyncio.run은 동기 함수에서 비동기 함수를 호출할 때 사용
        # _handle_image_generation_completion은 이미 async 함수이므로 직접 await할 수 없음
        # 따라서 여기서는 asyncio.run을 유지합니다.
        asyncio.run(_handle_image_generation_completion(
            task_id=task_id,
            status=status,
            image_url=image_url,
            message_from_callback=message_from_callback,
            conversation_id=conversation_id,
            original_prompt=original_prompt,
            style=style
        ))
        
        logger.info(f"Callback received for Task {task_id}: Status {status}, Image URL {image_url}")
        return JsonResponse({'status': 'success'})
    except json.JSONDecodeError:
        logger.error("Invalid JSON in image generation callback request.", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing image generation callback: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# [주석 처리] 이전 load_museum_data 함수 (위에서 수정된 함수 사용)
# def load_museum_data():
#     file_path = os.path.join(settings.BASE_DIR, 'gallery_data', 'cleaned_museum_data.json')
#     try:
#         with open(file_path, 'r', encoding='utf-8') as f:
#             data = json.load(f)
#         valid_museums = [
#             m for m in data
#             if 'latitude' in m and m['latitude'] is not None and
#                'longitude' in m and m['longitude'] is not None and
#                isinstance(m['latitude'], (int, float)) and
#                isinstance(m['longitude'], (int, float))
#         ]
#         return valid_museums
#     except FileNotFoundError:
#         print(f"Error: cleaned_museum_data.json not found at {file_path}")
#         return []
#     except json.JSONDecodeError:
#         print(f"Error: Could not decode JSON from {file_path}")
#         return []
#     except Exception as e:
#         print(f"An unexpected error occurred while loading museum data: {e}")
#         return []

# 전시관 목록을 제공하는 API 뷰 (이전과 동일)
def museum_list_api(request):
    museums = load_museum_data()
    return JsonResponse(museums, safe=False, json_dumps_params={'ensure_ascii': False})
