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

# llm_cores 디렉토리에서 번역 서비스 임포트
from llm_cores.translation_service import translate_text
# llm_cores 디렉토리에서 도슨트 서비스 임포트
from llm_cores.gemma_service import get_docent_response # Gemma 서비스 임포트

# image_logic_parser 임포트
from .image_logic_parser import generate_image_based_on_json_logic
# [추가 부분] positive_prompts.py에서 POSITIVE_PROMPT_MAP 임포트
from llm_cores.positive_prompts import POSITIVE_PROMPT_MAP
# [추가 부분] negative_prompts.py에서 NEGATIVE_PROMPT_MAP 임포트
from llm_cores.negative_prompts import NEGATIVE_PROMPT_MAP


logger = logging.getLogger(__name__)

# ComfyUI 관련 설정 (settings.py에서 가져옴)
# [주석 처리] 이 변수들은 이제 image_logic_parser.py에서 settings를 직접 참조하므로,
# views.py에서 generate_image_based_on_json_logic으로 직접 전달되지 않습니다.
# COMFYUI_API_URL = getattr(settings, 'COMFYUI_API_URL', "http://127.0.0.1:8188/prompt")
# COMFYUI_HISTORY_URL = getattr(settings, 'COMFYUI_HISTORY_URL', "http://127.0.0.1:8188/history")
# COMFYUI_IMAGE_URL = getattr(settings, 'COMFYUI_IMAGE_URL', "http://127.0.0.1:8188/view")
# COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', os.path.join(settings.BASE_DIR, 'comfyui_data', 'input'))
# COMFYUI_OUTPUT_DIR = getattr(settings, 'COMFYUI_OUTPUT_DIR', os.path.join(settings.BASE_DIR, 'comfyui_data', 'output'))


# --- 웹 페이지 렌더링 뷰 ---
# [복원 부분] 이전에 실수로 제거되었던 페이지 렌더링 뷰들을 복원합니다.
def welcome_view(request):
    return render(request, 'welcome.html')

def features_view(request):
    return render(request, 'features.html')

def about_view(request):
    return render(request, 'about.html')

def main_view(request):
    return render(request, 'main.html')

def gallery_view(request):
    return render(request, 'gallery.html')

def archive_view(request):
    return render(request, 'archive.html')


# --- API 뷰 ---

# generate_image_task 함수 - conversation_id와 image_data_base64, width, height, negative_prompt_categories, positive_prompt_categories 파라미터 추가
def generate_image_task(
    task_id,
    translated_prompt,
    conversation_id,
    image_data_base64=None,
    width=512,  # [추가 부분] 이미지 너비 인자 추가
    height=512, # [추가 부분] 이미지 높이 인자 추가
    negative_prompt_categories=None, # [추가 부분] 부정 프롬프트 카테고리 인자 추가
    positive_prompt_categories=None,  # [추가 부분] 긍정 프롬프트 카테고리 인자 추가
    style_name="generated" # [추가 부분] GeneratedImage 모델에 저장할 스타일 이름
):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        logger.info(f"Task {task_id}: Image generation started with prompt: '{translated_prompt}'")
        
        # 이미지 생성 로직 호출
        # [수정 부분] generate_image_based_on_json_logic 호출 시 인자 변경
        image_info = loop.run_until_complete(
            generate_image_based_on_json_logic(
                prompt=translated_prompt,
                negative_prompt_en="", # 현재는 빈 문자열로 고정 (카테고리로 대체)
                image_data_base64=image_data_base64,
                width=width,  # width 인자 전달
                height=height, # height 인자 전달
                negative_prompt_categories=negative_prompt_categories, # negative_prompt_categories 인자 전달
                positive_prompt_categories=positive_prompt_categories  # positive_prompt_categories 인자 전달
            )
        )
        loop.close() # 루프 닫기

        if image_info and image_info.get('image_file_path'): # .get() 사용으로 안전성 확보
            # 생성된 이미지 URL을 DB에 저장 (GeneratedImage 모델)
            image_relative_path = os.path.relpath(image_info['image_file_path'], settings.MEDIA_ROOT)
            generated_image_url = settings.MEDIA_URL + image_relative_path.replace(os.sep, '/')

            GeneratedImage.objects.create(
                title=translated_prompt,
                description=f"'{translated_prompt}' 프롬프트로 생성된 이미지.",
                prompt=translated_prompt,
                image_file=image_relative_path, # MEDIA_ROOT 기준 상대 경로 저장
                style=style_name, # [수정 부분] 동적으로 받은 style_name 저장
                image_type='i2i' if image_data_base64 else 't2i', # i2i 여부 판단
                created_at=timezone.now()
            )
            logger.info(f"생성된 이미지 DB 저장 완료: {generated_image_url}")

            cache.set(task_id, {
                'status': 'SUCCESS',
                'message': '이미지 생성 완료!',
                'image_url': generated_image_url,
                'conversation_id': conversation_id # conversation_id 유지
            })
            logger.info(f"Task {task_id} 성공: 이미지 URL = {generated_image_url}")
        else:
            cache.set(task_id, {
                'status': 'FAILURE',
                'message': '이미지 생성 실패: 유효한 이미지 정보를 얻지 못했습니다.',
                'conversation_id': conversation_id # conversation_id 유지
            })
            logger.error(f"Task {task_id} 실패: 유효한 이미지 정보를 얻지 못함.")
    except Exception as e:
        logger.error(f"이미지 생성 작업 중 예외 발생 (Task {task_id}): {e}", exc_info=True)
        cache.set(task_id, {
            'status': 'FAILURE',
            'message': f'이미지 생성 중 오류 발생: {e}',
            'conversation_id': conversation_id
        })
    finally:
        # [추가 부분] 루프가 닫히지 않은 경우를 대비하여 추가
        if not loop.is_closed():
            loop.close()


# process_request_api 함수 - 이미지 분석 및 이미지 생성 로직 통합
@csrf_exempt
@require_POST
def process_request_api(request):
    try:
        user_input = request.POST.get('user_input', '').strip()
        conversation_id_str = request.POST.get('conversation_id', 'new-chat')
        mode = request.POST.get('mode', 'curator') # 'curator' 또는 'image_generation'

        # [추가 부분] 프론트엔드에서 전송된 카테고리 데이터 파싱
        # 프론트엔드에서 JSON 문자열 형태로 전송한다고 가정합니다.
        # 예: '["korean_ink_wash_style", "landscape_painting_style"]'
        positive_categories_json = request.POST.get('positive_categories_json', '[]')
        negative_categories_json = request.POST.get('negative_categories_json', '[]')
        
        try:
            positive_prompt_categories = json.loads(positive_categories_json)
            negative_prompt_categories = json.loads(negative_categories_json)
        except json.JSONDecodeError:
            logger.error("Positive or negative categories JSON parsing error. Using empty lists.")
            positive_prompt_categories = []
            negative_prompt_categories = []

        # [추가 부분] 최종 스타일 이름 결정 (GeneratedImage 모델에 저장할 용도)
        # 여러 카테고리가 선택될 수 있으므로, 이를 조합하여 스타일 이름을 생성합니다.
        # 여기서는 긍정 프롬프트 카테고리를 콤마로 연결하여 사용합니다.
        style_name = ", ".join(positive_prompt_categories) if positive_prompt_categories else "generated"


        # 이미지 파일 처리 로직
        image_file = request.FILES.get('image_file')
        image_data_base64 = None
        user_uploaded_image_url = None # 사용자가 업로드한 이미지의 URL

        if image_file:
            # 파일을 메모리에서 읽어 Base64로 인코딩
            image_bytes = image_file.read()
            image_data_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # 사용자 이미지 저장 (영구 표시를 위해 권장)
            # 파일 이름을 고유하게 만들기 (예: uuid 사용)
            file_extension = os.path.splitext(image_file.name)[1]
            unique_filename = f"user_uploads/{uuid.uuid4().hex}{file_extension}"
            file_path = default_storage.save(unique_filename, image_file)
            user_uploaded_image_url = default_storage.url(file_path)
            logger.info(f"사용자 이미지 저장됨: {user_uploaded_image_url}")


        # 대화 ID 관리
        if conversation_id_str == 'new-chat':
            conversation = Conversation.objects.create(session_id=str(uuid.uuid4()))
            conversation_id = str(conversation.session_id)
        else:
            try:
                conversation = Conversation.objects.get(session_id=conversation_id_str)
                conversation_id = conversation_id_str
            except Conversation.DoesNotExist:
                conversation = Conversation.objects.create(session_id=str(uuid.uuid4()))
                conversation_id = str(conversation.session_id)
                logger.warning(f"기존 대화 ID {conversation_id_str}를 찾을 수 없어 새 대화 시작.")


        # 사용자 메시지 저장 (이미지 URL 포함)
        user_message = Message.objects.create(
            conversation=conversation,
            sender='user',
            text=user_input,
            image_url=user_uploaded_image_url # 업로드된 이미지 URL 저장
        )
        logger.info(f"사용자 메시지 저장됨: {user_message.text} (이미지: {user_message.image_url})")


        ai_response = ""
        task_id = None
        response_image_url = None

        if mode == 'image_generation':
            # 이미지 생성 모드
            logger.info(f"이미지 생성 모드: 프롬프트 '{user_input}'")
            # [수정 부분] translate_text 함수 호출 시 source_lang 인자 추가
            translated_prompt = translate_text(user_input, source_lang='ko', target_lang='en')
            logger.info(f"번역된 프롬프트 (EN): '{translated_prompt}'")

            # generate_image_based_on_json_logic 함수는 비동기적으로 실행되어야 합니다.
            # ComfyUI와의 통신은 시간이 오래 걸릴 수 있으므로 스레딩을 사용합니다.
            task_id = str(uuid.uuid4())
            cache.set(task_id, {'status': 'PENDING', 'message': '이미지 생성 요청 접수됨.'}, timeout=3600) # 1시간 TTL
            
            logger.info(f"Starting image generation task {task_id} for conversation {conversation_id}")
            
            # [수정 부분] generate_image_task에 전달할 인자 변경 (width, height, negative_prompt_categories, positive_prompt_categories, style_name 추가)
            # 이 값들은 이제 프론트엔드에서 전송되거나, 기본값으로 사용됩니다.
            thread_args = (
                task_id,
                translated_prompt,
                conversation_id,
                image_data_base64,
                512, # width (기본값)
                512, # height (기본값)
                negative_prompt_categories, # [수정 부분] 파싱된 부정 프롬프트 카테고리 전달
                positive_prompt_categories, # [수정 부분] 파싱된 긍정 프롬프트 카테고리 전달
                style_name # [추가 부분] 결정된 스타일 이름 전달
            )
            thread = threading.Thread(target=generate_image_task, args=thread_args)
            thread.start()

            return JsonResponse({'status': 'processing', 'task_id': task_id, 'conversation_id': conversation_id, 'user_image_url': user_uploaded_image_url})
        
        else: # 'curator' 모드
            logger.info(f"큐레이터 모드: 프롬프트 '{user_input}', 이미지 존재 여부: {bool(image_file)}")
            # [수정 부분] get_docent_response에 image_data_base64 전달
            docent_response_text = get_docent_response(prompt=user_input, image_data_base64=image_data_base64)
            ai_response = docent_response_text
            logger.info(f"Gemma 응답: '{ai_response}'")

            # AI 응답 메시지 저장
            ai_message = Message.objects.create(
                conversation=conversation,
                sender='ai',
                text=ai_response,
                # AI가 이미지 분석 후 이미지를 생성하지 않는 한 image_url은 None
                image_url=None
            )
            logger.info(f"AI 응답 메시지 저장됨: {ai_message.text}")

            return JsonResponse({'status': 'success', 'ai_response': ai_response, 'conversation_id': conversation_id, 'user_image_url': user_uploaded_image_url})

    except json.JSONDecodeError:
        logger.error("JSON 파싱 오류: 유효하지 않은 JSON 요청입니다.")
        return JsonResponse({'status': 'error', 'message': '유효하지 않은 JSON 요청입니다.'}, status=400)
    except Exception as e:
        logger.error(f"process_request_api 처리 중 예외 발생: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'서버 내부 오류가 발생했습니다: {e}'}, status=500)


# check_task_status_api 함수 - conversation_id 반환
@csrf_exempt
@require_GET
def check_task_status_api(request, task_id):
    status_data = cache.get(str(task_id))
    if status_data:
        # conversation_id도 함께 반환
        return JsonResponse(status_data)
    else:
        return JsonResponse({'status': 'UNKNOWN', 'message': '알 수 없거나 만료된 작업 ID입니다.'}, status=404)

# 대화 기록 API
@csrf_exempt
@require_GET
def get_conversations_api(request):
    """
    모든 대화 목록을 반환합니다.
    """
    conversations = Conversation.objects.all().order_by('-created_at')
    data = []
    for conv in conversations:
        # 각 대화의 마지막 메시지를 요약으로 사용 (선택 사항)
        last_message = conv.messages.order_by('-timestamp').first()
        data.append({
            'conversation_id': str(conv.session_id),
            'created_at': conv.created_at.isoformat(),
            'last_message_preview': last_message.text[:50] + '...' if last_message and last_message.text else '새 대화',
            'has_image': conv.messages.filter(image_url__isnull=False).exists() # 대화에 이미지가 포함되었는지 여부
        })
    return JsonResponse(data, safe=False)

@csrf_exempt
@require_GET
def get_conversation_history_api(request, conversation_id):
    """
    특정 대화 ID에 대한 전체 메시지 기록을 반환합니다.
    """
    try:
        conversation = Conversation.objects.get(session_id=conversation_id)
        messages = conversation.messages.all().order_by('timestamp')
        history = []
        for msg in messages:
            history.append({
                'sender': msg.sender,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
                'image_url': msg.image_url if msg.image_url else None # 이미지 URL 포함
            })
        return JsonResponse({'status': 'success', 'history': history, 'conversation_id': str(conversation.session_id)})
    except Conversation.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '대화를 찾을 수 없습니다.'}, status=404)
    except Exception as e:
        logger.error(f"대화 기록 조회 중 오류 발생: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': '대화 기록 조회 중 오류 발생'}, status=500)


# 이미지 갤러리 API (기존 api_get_images 함수)
@csrf_exempt
@require_GET
def api_get_images(request):
    search_query = request.GET.get('search', '')
    selected_style = request.GET.get('style', '')
    sort_order = request.GET.get('sort', 'latest') # 기본 정렬은 'latest'

    # Q 객체를 사용하여 OR 조건으로 검색 (제목, 설명, 프롬프트)
    images = GeneratedImage.objects.all()
    if search_query:
        images = images.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(prompt__icontains=search_query)
        )
    
    if selected_style:
        images = images.filter(style=selected_style)

    if sort_order == 'latest':
        images = images.order_by('-created_at')
    elif sort_order == 'popular':
        images = images.order_by('-views') 
    elif sort_order == 'random':
        images = images.order_by('?') 
    else: 
        images = images.order_by('-created_at')

    # --- 추가된 부분: 이미지 개수 제한 ---
    MAX_DISPLAY_COUNT = 6 
    images = images[:MAX_DISPLAY_COUNT] # 최대 6개까지만 가져옵니다.
    # -----------------------------------

    images_data = []
    for img in images:
        images_data.append({
            'id': img.id,
            'title': img.title,
            'description': img.description,
            'prompt': img.prompt,
            'image_file': img.image_file.url if img.image_file else '', 
            'views': img.views,
            'likes': img.likes,
            'style': img.style, 
            'created_at': img.created_at.isoformat() if img.created_at else None,
        })
    
    return JsonResponse(images_data, safe=False)

# [주석 처리] 사용하지 않거나 통합된 API 뷰
# @csrf_exempt
# @require_POST
# def process_curator_request_api(request):
#     # 이 함수는 이제 process_request_api로 통합됩니다.
#     pass

# [주석 처리] 사용하지 않거나 통합된 API 뷰
# @csrf_exempt
# @require_POST
# def process_image_generation_request_api(request):
#     # 이 함수는 이제 process_request_api로 통합됩니다.
#     pass

# [주석 처리] 이미지 업로드 후 저장하는 별도의 뷰 (선택 사항, 현재는 process_request_api에 통합)
# @csrf_exempt
# @require_POST
# def upload_image_api(request):
#     if 'image_file' in request.FILES:
#         uploaded_file = request.FILES['image_file']
#         try:
#             # 파일 이름 충돌 방지를 위해 UUID 사용
#             file_extension = os.path.splitext(uploaded_file.name)[1]
#             unique_filename = f"user_uploads/{uuid.uuid4()}{file_extension}"
#             file_path = default_storage.save(unique_filename, uploaded...
