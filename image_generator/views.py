import threading
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.cache import cache
from django.conf import settings
from django.core.files.storage import default_storage # FileSystemStorage 대신 default_storage 사용
from django.shortcuts import render
from .models import GeneratedImage # GeneratedImage 모델 import 필요
from django.db.models import Q # Q 객체 import (검색 필터링에 사용)
from collections import defaultdict
import os
import json
import time
import httpx
import random
import traceback
import logging

# llm_cores 디렉토리에서 번역 서비스 임포트
from llm_cores.translation_service import translate_text
# llm_cores 디렉토리에서 도슨트 서비스 임포트
from llm_cores.gemma_service import get_docent_response # Gemma 서비스 임포트

# image_logic_parser 임포트
from .image_logic_parser import generate_image_based_on_json_logic

logger = logging.getLogger(__name__)

# ComfyUI 관련 설정 (settings.py에서 가져오기, 기본값 지정)
COMFYUI_API_URL = getattr(settings, 'COMFYUI_API_URL', "http://127.0.0.1:8188/prompt")
COMFYUI_HISTORY_URL = getattr(settings, 'COMFYUI_HISTORY_URL', "http://127.0.0.1:8188/history")
COMFYUI_IMAGE_URL = getattr(settings, 'COMFYUI_IMAGE_URL', "http://127.0.0.1:8188/view")
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', os.path.join(settings.MEDIA_ROOT, 'comfyui_input'))

# 인메모리 대화 저장소 (임시, 실제 서비스에서는 DB 사용 권장)
# {
#   'conversation_id': {
#       'title': '대화 제목',
#       'messages': [
#           {'speaker': 'user', 'text': '안녕'},
#           {'speaker': 'ai', 'text': '안녕하세요!'},
#           {'speaker': 'user', 'text': '이미지 생성해줘', 'image_url': 'path/to/image.jpg'},
#           {'speaker': 'ai', 'text': '이미지 생성 완료', 'image_url': 'path/to/generated_image.jpg'}
#       ]
#   }
# }
temp_conversations_db = {}
conversation_lock = threading.Lock() # 대화 기록에 동시 접근을 막기 위한 락

# 비동기 작업의 상태를 저장하는 딕셔너리 (task_id: {"status": "PENDING", "message": "...", "image_url": null})
task_status_db = {}
task_status_lock = threading.Lock() # 작업 상태에 동시 접근을 막기 위한 락

# Helper function to send prompt to ComfyUI
def queue_prompt(prompt_workflow):
    """
    ComfyUI에 프롬프트(워크플로우)를 전송하고 task_id를 반환합니다.
    """
    p = {"prompt": prompt_workflow}
    headers = {"Content-Type": "application/json"}
    try:
        response = httpx.post(COMFYUI_API_URL, headers=headers, json=p, timeout=30)
        response.raise_for_status() # HTTP 오류가 발생하면 예외 발생
        data = response.json()
        prompt_id = data.get('prompt_id')
        logger.info(f"ComfyUI prompt queued. Prompt ID: {prompt_id}")
        return prompt_id
    except httpx.RequestError as e:
        logger.error(f"ComfyUI API request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from ComfyUI response: {e}, Response: {response.text}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while queuing prompt: {e}")
        return None

# Helper function to get image from ComfyUI history
def get_image(filename, subfolder, folder_type):
    """
    ComfyUI로부터 이미지를 가져와 Django STATIC_ROOT에 저장하고 URL을 반환합니다.
    """
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    headers = {"Content-Type": "application/json"}
    try:
        response = httpx.get(COMFYUI_IMAGE_URL, headers=headers, params=data, timeout=30)
        response.raise_for_status()
        
        # 이미지 파일명 (UUID 포함)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        
        # Django의 MEDIA_ROOT에 저장
        image_path = os.path.join(settings.MEDIA_ROOT, 'generated_images', unique_filename)
        os.makedirs(os.path.dirname(image_path), exist_ok=True) # 디렉토리 생성
        
        with open(image_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Image saved to {image_path}")
        # MEDIA_URL을 사용하여 URL 반환
        return settings.MEDIA_URL + 'generated_images/' + unique_filename
    except httpx.RequestError as e:
        logger.error(f"ComfyUI image retrieval failed: {e}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting image: {e}")
        return None

# Helper function to get history from ComfyUI
def get_history(prompt_id):
    """
    주어진 prompt_id에 대한 ComfyUI 작업 이력을 조회합니다.
    """
    try:
        response = httpx.get(f"{COMFYUI_HISTORY_URL}?prompt_id={prompt_id}", timeout=30)
        response.raise_for_status()
        history = response.json()
        return history
    except httpx.RequestError as e:
        logger.error(f"ComfyUI history retrieval failed for prompt_id {prompt_id}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from ComfyUI history response: {e}, Response: {response.text}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while getting history: {e}")
        return None

# --- ComfyUI 관련 API 뷰들 (main.js에서 통합 API로 대체되므로 주석 처리 또는 통합) ---

# @csrf_exempt
# @require_POST
# def generate_image_view(request):
#     """
#     텍스트 프롬프트를 받아 ComfyUI에 이미지 생성 요청을 보내고 task_id를 반환합니다.
#     """
#     try:
#         data = json.loads(request.body)
#         prompt = data.get('prompt')
#         conversation_id = data.get('conversation_id') # 대화 ID 추가

#         if not prompt:
#             return JsonResponse({"status": "error", "message": "프롬프트가 필요합니다."}, status=400)

#         # 여기서 ComfyUI 워크플로우 로드 및 prompt_id 반환
#         # (generate_image_based_on_json_logic 함수 사용)
#         # 예시: 워크플로우 JSON 파일 로드 (여기서는 text_to_image.json 가정)
#         workflow_path = os.path.join(settings.BASE_DIR, 'image_generator', 'workflows', 'text_to_image.json')
#         with open(workflow_path, 'r', encoding='utf-8') as f:
#             workflow = json.load(f)

#         # 프롬프트 업데이트 (6번 노드의 'text' 필드)
#         if "6" in workflow["prompt"] and "inputs" in workflow["prompt"]["6"]:
#             workflow["prompt"]["6"]["inputs"]["text"] = prompt
#         else:
#             logger.warning("Workflow does not contain node 6 for text prompt. Using default.")

#         prompt_id = queue_prompt(workflow)

#         if prompt_id:
#             task_id = str(uuid.uuid4())
#             with task_status_lock:
#                 task_status_db[task_id] = {
#                     "status": "PENDING",
#                     "message": "이미지 생성을 시작합니다...",
#                     "prompt_id": prompt_id,
#                     "image_url": None
#                 }
#             # 대화 기록에 사용자 메시지 추가 (이미지 생성 요청)
#             with conversation_lock:
#                 if conversation_id not in temp_conversations_db:
#                     temp_conversations_db[conversation_id] = {'title': prompt[:30], 'messages': []}
#                 temp_conversations_db[conversation_id]['messages'].append({'speaker': 'user', 'text': prompt})

#             return JsonResponse({"status": "success", "task_id": task_id, "conversation_id": conversation_id})
#         else:
#             return JsonResponse({"status": "error", "message": "이미지 생성 요청에 실패했습니다."}, status=500)
#     except json.JSONDecodeError:
#         return JsonResponse({"status": "error", "message": "유효하지 않은 JSON 형식입니다."}, status=400)
#     except Exception as e:
#         logger.error(f"Error in generate_image_view: {traceback.format_exc()}")
#         return JsonResponse({"status": "error", "message": f"서버 오류: {e}"}, status=500)


# @require_GET
# def check_image_status_view(request, task_id):
#     """
#     생성된 이미지의 상태를 확인하고, 완료되면 이미지 URL을 반환합니다.
#     """
#     with task_status_lock:
#         task_info = task_status_db.get(str(task_id))

#     if not task_info:
#         return JsonResponse({"status": "error", "message": "유효하지 않거나 만료된 작업 ID입니다."}, status=404)

#     if task_info["status"] == "SUCCESS":
#         return JsonResponse({"status": "SUCCESS", "message": "이미지 생성 완료.", "image_url": task_info["image_url"]})
#     elif task_info["status"] == "FAILURE":
#         return JsonResponse({"status": "FAILURE", "message": task_info.get("message", "이미지 생성 실패.")})
#     else: # PENDING or PROGRESS
#         prompt_id = task_info.get("prompt_id")
#         if not prompt_id:
#             return JsonResponse({"status": "FAILURE", "message": "유효한 prompt_id가 없습니다."}, status=500)

#         history = get_history(prompt_id)
#         if history:
#             # ComfyUI history에서 이미지 파일명 추출 및 처리
#             # 이 부분은 ComfyUI 워크플로우의 Save Image 노드 설정에 따라 달라집니다.
#             # 여기서는 기본 SimpleSave 노드를 가정합니다.
#             if prompt_id in history:
#                 outputs = history[prompt_id].get('outputs', {})
#                 image_data_list = []
#                 for node_id, node_output in outputs.items():
#                     if 'images' in node_output:
#                         for img in node_output['images']:
#                             image_data_list.append({
#                                 "filename": img.get("filename"),
#                                 "subfolder": img.get("subfolder"),
#                                 "type": img.get("type")
#                             })
                
#                 if image_data_list:
#                     # 첫 번째 이미지 파일만 처리 (단일 이미지 생성을 가정)
#                     first_image = image_data_list[0]
#                     image_url = get_image(first_image['filename'], first_image['subfolder'], first_image['type'])
                    
#                     if image_url:
#                         with task_status_lock:
#                             task_status_db[str(task_id)]["status"] = "SUCCESS"
#                             task_status_db[str(task_id)]["message"] = "이미지 생성 완료."
#                             task_status_db[str(task_id)]["image_url"] = image_url
#                         logger.info(f"Task {task_id}: Image generated and URL saved: {image_url}")
#                         return JsonResponse({"status": "SUCCESS", "message": "이미지 생성 완료.", "image_url": image_url})
#                     else:
#                         with task_status_lock:
#                             task_status_db[str(task_id)]["status"] = "FAILURE"
#                             task_status_db[str(task_id)]["message"] = "이미지를 가져오는 데 실패했습니다."
#                         logger.error(f"Task {task_id}: Failed to get image from ComfyUI.")
#                         return JsonResponse({"status": "FAILURE", "message": "이미지를 가져오는 데 실패했습니다."})
#             else:
#                 logger.info(f"Task {task_id}: ComfyUI history for prompt_id {prompt_id} not yet available.")
#                 return JsonResponse({"status": "PROGRESS", "message": "이미지 생성 중...", "progress": "50%"}) # 진행 상태 업데이트 예시
#         else:
#             logger.warning(f"Task {task_id}: Could not retrieve history for prompt_id {prompt_id}. Still pending.")
#             return JsonResponse({"status": "PENDING", "message": "ComfyUI 작업 대기 중...", "progress": "10%"}) # 초기 진행 상태

# @csrf_exempt
# @require_POST
# def chat_with_ai_docent_view(request):
#     """
#     사용자 메시지를 받아 AI 도슨트(Gemma)로부터 응답을 받습니다.
#     """
#     try:
#         data = json.loads(request.body)
#         user_message = data.get('user_message')
#         conversation_id = data.get('conversation_id') # 대화 ID 추가

#         if not user_message:
#             return JsonResponse({"status": "error", "message": "메시지가 필요합니다."}, status=400)

#         # Gemini Gemma 모델을 사용하여 도슨트 응답 생성
#         ai_response = get_docent_response(user_message)

#         # 대화 기록에 사용자 메시지 및 AI 응답 추가
#         with conversation_lock:
#             if conversation_id not in temp_conversations_db:
#                 temp_conversations_db[conversation_id] = {'title': user_message[:30], 'messages': []}
#             temp_conversations_db[conversation_id]['messages'].append({'speaker': 'user', 'text': user_message})
#             temp_conversations_db[conversation_id]['messages'].append({'speaker': 'ai', 'text': ai_response})

#         return JsonResponse({"status": "success", "ai_response": ai_response, "conversation_id": conversation_id})
#     except json.JSONDecodeError:
#         return JsonResponse({"status": "error", "message": "유효하지 않은 JSON 형식입니다."}, status=400)
#     except Exception as e:
#         logger.error(f"Error in chat_with_ai_docent_view: {traceback.format_exc()}")
#         return JsonResponse({"status": "error", "message": f"서버 오류: {e}"}, status=500)

@csrf_exempt
@require_POST
def process_request_api(request):
    """
    사용자의 요청 (텍스트 메시지 또는 이미지 생성 프롬프트 + 이미지 파일)을 받아 처리하고
    작업 ID 또는 직접적인 AI 응답을 반환합니다.
    main.js에서 /api/process_request/ 로 통합 요청이 들어옵니다.
    """
    try:
        user_input = request.POST.get('user_input')
        conversation_id = request.POST.get('conversation_id')
        mode = request.POST.get('mode', 'curator') # 기본 모드는 'curator'
        image_file = request.FILES.get('image_file') # 업로드된 이미지 파일
        negative_prompt = request.POST.get('negative_prompt', '')

        if not user_input and not image_file:
            return JsonResponse({"status": "error", "message": "메시지 또는 이미지가 필요합니다."}, status=400)

        # 새 대화인 경우, 새 conversation_id 생성
        if conversation_id == 'new-chat' or not conversation_id:
            conversation_id = str(uuid.uuid4())
            with conversation_lock:
                temp_conversations_db[conversation_id] = {'title': user_input[:30] if user_input else 'New Chat', 'messages': []}
            logger.info(f"New conversation created: {conversation_id}")

        # 사용자 메시지(및 이미지)를 대화 기록에 추가
        user_message_entry = {'speaker': 'user', 'text': user_input}
        if image_file:
            # 업로드된 이미지 저장
            fs = default_storage
            # 고유한 파일 이름 생성 (UUID를 사용하여 이름 충돌 방지)
            file_extension = os.path.splitext(image_file.name)[1]
            unique_filename = f"uploads/{uuid.uuid4()}{file_extension}"
            file_path = fs.save(unique_filename, image_file)
            user_message_entry['image_url'] = fs.url(file_path) # MEDIA_URL을 포함한 URL
            logger.info(f"User uploaded image saved: {file_path}")

        with conversation_lock:
            temp_conversations_db[conversation_id]['messages'].append(user_message_entry)

        if mode == 'image_generation':
            # 이미지 생성 로직
            logger.info(f"Image generation request for conversation {conversation_id} with input: '{user_input}' and image_file: {image_file is not None}")
            
            # ComfyUI 워크플로우 로드
            workflow_file = 'i2i_controlnet.json' if image_file else 'text_to_image.json'
            workflow_path = os.path.join(settings.BASE_DIR, 'image_generator', 'workflows', workflow_file)

            if not os.path.exists(workflow_path):
                logger.error(f"Workflow file not found: {workflow_path}")
                return JsonResponse({"status": "error", "message": f"워크플로우 파일을 찾을 수 없습니다: {workflow_file}"}, status=500)

            with open(workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
            
            # `generate_image_based_on_json_logic` 함수를 사용하여 워크플로우 업데이트 및 큐에 추가
            task_id = str(uuid.uuid4())
            with task_status_lock:
                task_status_db[task_id] = {
                    "status": "PENDING",
                    "message": "이미지 생성을 시작합니다...",
                    "prompt_id": None, # 나중에 업데이트될 것
                    "image_url": None,
                    "conversation_id": conversation_id # 어떤 대화에 속한 태스크인지 저장
                }
            
            # 비동기로 이미지 생성 시작
            # (실제 프로덕션에서는 Celery 같은 태스크 큐 사용 권장)
            threading.Thread(target=generate_image_task, args=(task_id, workflow, user_input, image_file, negative_prompt)).start()
            
            return JsonResponse({"status": "success", "task_id": task_id, "conversation_id": conversation_id})

        else: # 'curator' 모드 또는 기본 동작
            # AI 도슨트 응답 생성 로직
            logger.info(f"Curator mode request for conversation {conversation_id} with input: '{user_input}'")
            if not user_input:
                return JsonResponse({"status": "error", "message": "큐레이터 모드에서는 텍스트 입력이 필요합니다."}, status=400)
            
            ai_response = get_docent_response(user_input)

            # AI 응답을 대화 기록에 추가
            with conversation_lock:
                temp_conversations_db[conversation_id]['messages'].append({'speaker': 'ai', 'text': ai_response})

            return JsonResponse({"status": "success", "ai_response": ai_response, "conversation_id": conversation_id})

    except json.JSONDecodeError:
        logger.error(f"JSON Decode Error in process_request_api: {traceback.format_exc()}")
        return JsonResponse({"status": "error", "message": "유효하지 않은 JSON 형식입니다."}, status=400)
    except Exception as e:
        logger.error(f"Error in process_request_api: {traceback.format_exc()}")
        return JsonResponse({"status": "error", "message": f"서버 오류: {e}"}, status=500)

def generate_image_task(task_id, workflow, user_input, image_file, negative_prompt):
    """
    이미지 생성을 비동기로 처리하는 함수.
    이 함수는 별도의 스레드에서 실행됩니다.
    """
    try:
        # `generate_image_based_on_json_logic` 함수는 workflow를 직접 수정하고 prompt_id를 반환
        logger.debug(f"Starting image generation task {task_id}")
        
        # 이미지 파일이 있다면, 해당 경로를 전달 (default_storage.path() 사용)
        image_file_path = None
        if image_file:
            # default_storage.path()는 실제 파일 시스템 경로를 반환합니다.
            # 이 경로는 ComfyUI의 input 디렉토리 내에 있어야 합니다.
            # ComfyUI가 직접 파일 시스템 경로를 읽을 수 있도록 설정되어 있다고 가정합니다.
            
            # 먼저 image_file을 ComfyUI input 디렉토리로 복사
            fs = default_storage
            original_filename = image_file.name
            
            # ComfyUI input 디렉토리에 저장할 고유한 이름
            comfy_input_filename = f"{uuid.uuid4()}_{original_filename}"
            comfy_input_filepath = os.path.join(COMFYUI_INPUT_DIR, comfy_input_filename)

            # 이미지 파일을 ComfyUI input 디렉토리에 저장
            # default_storage의 save 함수를 사용하면 MEDIA_ROOT 내에 저장되므로,
            # ComfyUI_INPUT_DIR 경로로 직접 파일을 쓰는 로직이 필요합니다.
            os.makedirs(COMFYUI_INPUT_DIR, exist_ok=True)
            with open(comfy_input_filepath, 'wb+') as destination:
                for chunk in image_file.chunks():
                    destination.write(chunk)
            
            image_file_path = comfy_input_filename # ComfyUI가 사용할 파일 이름만 전달

            logger.info(f"User uploaded image copied to ComfyUI input dir: {comfy_input_filepath}")
        
        prompt_id = generate_image_based_on_json_logic(
            workflow,
            user_input,
            negative_prompt,
            image_file_path # ComfyUI input 디렉토리에 저장된 파일 이름 전달
        )

        if not prompt_id:
            raise Exception("Failed to queue prompt to ComfyUI.")

        with task_status_lock:
            task_status_db[task_id]["prompt_id"] = prompt_id
            task_status_db[task_id]["message"] = "ComfyUI에 작업이 큐에 추가되었습니다. 이미지 생성 중..."
            task_status_db[task_id]["status"] = "PROGRESS"

        logger.info(f"Task {task_id}: Prompt queued with prompt_id {prompt_id}. Starting polling.")

        # 폴링 로직 (task_status_db를 직접 업데이트)
        polling_attempts = 0
        max_polling_attempts = 60 # 2초 * 60 = 120초 (2분) 대기
        
        while polling_attempts < max_polling_attempts:
            time.sleep(2) # 2초 대기
            polling_attempts += 1
            
            history = get_history(prompt_id)
            if history and prompt_id in history:
                outputs = history[prompt_id].get('outputs', {})
                image_data_list = []
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        for img in node_output['images']:
                            image_data_list.append({
                                "filename": img.get("filename"),
                                "subfolder": img.get("subfolder"),
                                "type": img.get("type")
                            })
                
                if image_data_list:
                    first_image = image_data_list[0]
                    image_url = get_image(first_image['filename'], first_image['subfolder'], first_image['type'])
                    
                    if image_url:
                        with task_status_lock:
                            task_status_db[task_id]["status"] = "SUCCESS"
                            task_status_db[task_id]["message"] = "이미지 생성 완료."
                            task_status_db[task_id]["image_url"] = image_url
                        logger.info(f"Task {task_id}: Image generated and URL saved: {image_url}")
                        
                        # 대화 기록에 AI 응답 (이미지 포함) 추가
                        with conversation_lock:
                            conv_id = task_status_db[task_id]["conversation_id"]
                            if conv_id in temp_conversations_db:
                                temp_conversations_db[conv_id]['messages'].append({'speaker': 'ai', 'text': '요청하신 이미지가 생성되었습니다.', 'image_url': image_url})
                        break # 성공했으니 폴링 중지
                    else:
                        raise Exception("Failed to retrieve image URL from ComfyUI.")
            
            # 진행 상태 업데이트 (선택 사항)
            current_progress = int((polling_attempts / max_polling_attempts) * 100)
            with task_status_lock:
                task_status_db[task_id]["message"] = f"이미지 생성 중... ({current_progress}%)"
                task_status_db[task_id]["progress"] = current_progress

        else: # max_polling_attempts 초과
            raise Exception("Image generation timed out.")

    except Exception as e:
        logger.error(f"Error in generate_image_task for task {task_id}: {traceback.format_exc()}")
        with task_status_lock:
            task_status_db[task_id]["status"] = "FAILURE"
            task_status_db[task_id]["message"] = f"이미지 생성 실패: {e}"
        
        # 실패 메시지를 대화 기록에 추가
        with conversation_lock:
            conv_id = task_status_db[task_id]["conversation_id"]
            if conv_id in temp_conversations_db:
                temp_conversations_db[conv_id]['messages'].append({'speaker': 'ai', 'text': f"이미지 생성에 실패했습니다: {e}"})

# --- 대화 기록 관련 API 뷰들 ---
@require_GET
def get_conversations_api(request): # get_all_conversations_api -> get_conversations_api로 변경
    """
    모든 대화 목록 (ID와 제목)을 반환하는 API 엔드포인트.
    """
    global temp_conversations_db
    with conversation_lock:
        conversations_list = []
        # 최신순으로 정렬 (예: uuid 기반이므로 생성 시간 순서는 아님, 실제 DB에서는 created_at 사용)
        # 여기서는 단순히 딕셔너리의 순서를 따르거나, 필요하다면 정렬 로직 추가
        for conv_id, conv_data in temp_conversations_db.items():
            # 첫 번째 메시지를 제목으로 사용하거나, 'New Chat'으로 대체
            # 만약 대화에 메시지가 없다면 'New Chat'으로, 아니면 첫 번째 메시지의 일부를 제목으로
            title = conv_data.get('title')
            if not title and conv_data['messages']:
                first_message_text = conv_data['messages'][0].get('text', 'No Text')
                title = first_message_text[:30] + '...' if len(first_message_text) > 30 else first_message_text
            elif not title:
                title = 'New Chat'

            conversations_list.append({
                "id": conv_id,
                "title": title
            })
        
        # 최신 대화가 위에 오도록 역순 정렬 (임시)
        # 실제 DB에서는 created_at 필드를 사용하여 정렬
        conversations_list.reverse() # 간단하게 뒤집어서 최신 대화처럼 보이게 함
        
        logger.debug(f"Returning {len(conversations_list)} conversations.")
        return JsonResponse({"conversations": conversations_list})

@require_GET
def get_conversation_messages_api(request, conversation_id): # <--- 새로 추가된 대화 메시지 API 뷰
    """
    특정 대화 ID에 해당하는 메시지 목록을 반환하는 API 엔드포인트.
    """
    global temp_conversations_db
    with conversation_lock:
        conversation = temp_conversations_db.get(conversation_id)
        if conversation:
            logger.debug(f"Returning {len(conversation['messages'])} messages for conversation {conversation_id}.")
            return JsonResponse({"messages": conversation["messages"]})
        else:
            logger.warning(f"Conversation {conversation_id} not found for message retrieval.")
            return JsonResponse({"status": "error", "message": "대화를 찾을 수 없습니다."}, status=404)

@require_GET
def check_task_status_api(request, task_id): # check_image_status_view -> check_task_status_api로 변경
    """
    주어진 task_id의 비동기 작업 상태를 반환하는 API 엔드포인트.
    main.js에서 /api/task-status/<uuid:task_id>/ 로 호출됩니다.
    """
    with task_status_lock:
        task_info = task_status_db.get(str(task_id))

    if not task_info:
        logger.warning(f"Task ID {task_id} not found in task_status_db.")
        return JsonResponse({"status": "FAILURE", "message": "유효하지 않거나 만료된 작업 ID입니다."}, status=404)
    
    logger.debug(f"Returning status for task {task_id}: {task_info['status']}")
    return JsonResponse(task_info)


# 1페이지 (루트 URL) - 간단한 웰컴 페이지 역할
@require_GET
def welcome_view(request):
    """
    루트 페이지를 렌더링합니다. (templates/welcome.html)
    """
    return render(request, 'welcome.html', {})

# 2페이지 (/features/) - 주요 기능 또는 서비스
@require_GET
def features_view(request):
    """
    주요 기능 또는 서비스를 설명하는 페이지를 렌더링합니다.
    (templates/features.html 또는 적절한 새 템플릿)
    """
    return render(request, 'features.html', {})

# 3페이지 (/about/) - 우리는 누구...
@require_GET
def about_view(request):
    """
    '소개' 페이지를 렌더링합니다. (templates/about.html)
    """
    return render(request, 'about.html', {})

# 4페이지 (/main/) - 메인 채팅/이미지 생성 페이지
@require_GET
def main_view(request):
    """
    메인 채팅/이미지 생성 페이지를 렌더링합니다. (templates/main.html)
    """
    return render(request, 'main.html', {})

# 5페이지 (/gallery/) - 전시관/미술관 찾기 페이지
# [수정 사항] gallery_view 함수 수정 - 정적 데이터 직접 전달
def gallery_view(request):
    # [추가 사항] 정적 전시관/미술관 데이터 정의
    # 실제 환경에서는 이 데이터를 데이터베이스에서 가져와야 하지만,
    # models.py 접근을 피하기 위해 임시로 여기에 정의합니다.
    museums_data = [
        {
            'id': 1,
            'name': "국립현대미술관 서울관",
            'address': "서울특별시 종로구 삼청로 30",
            'phone_number': "02-3701-9500",
            'operating_hours': "10:00 - 18:00 (월요일 휴관)",
            'description': "다양한 현대미술 작품을 만날 수 있는 곳입니다. 한국 근현대미술의 흐름과 세계 미술의 동향을 탐색하는 주요 기관입니다.",
            'website': "https://www.mmca.go.kr",
            'image_url': settings.STATIC_URL + 'images/museum_mmca_seoul.jpg', # STATIC_URL 사용
            'region': "seoul",
            'type': "art_museum"
        },
        {
            'id': 2,
            'name': "디뮤지엄",
            'address': "서울특별시 성동구 왕십리로83-21",
            'phone_number': "02-1670-0062",
            'operating_hours': "11:00 - 19:00 (월요일 휴관)",
            'description': "젊고 감각적인 전시가 열리는 미술관입니다. 현대미술, 디자인, 사진 등 다양한 장르의 전시를 선보입니다.",
            'website': "https://www.dmuseum.org",
            'image_url': settings.STATIC_URL + 'images/museum_dmuseum.jpg',
            'region': "seoul",
            'type': "gallery"
        },
        {
            'id': 3,
            'name': "부산시립미술관",
            'address': "부산광역시 해운대구 APEC로 58",
            'phone_number': "051-740-4200",
            'operating_hours': "10:00 - 18:00 (월요일 휴관)",
            'description': "부산 지역을 대표하는 공립 미술관입니다. 다양한 기획 전시와 교육 프로그램을 운영합니다.",
            'website': "http://art.busan.go.kr/",
            'image_url': settings.STATIC_URL + 'images/museum_busan.jpg',
            'region': "busan",
            'type': "art_museum"
        },
        {
            'id': 4,
            'name': "서울시립미술관 서소문본관",
            'address': "서울특별시 중구 덕수궁길 61",
            'phone_number': "02-2124-8800",
            'operating_hours': "10:00 - 20:00 (월요일 휴관)",
            'description': "근대에서 현대까지 다양한 예술을 전시합니다. 덕수궁 옆에 위치하여 접근성이 좋습니다.",
            'website': "https://sema.seoul.go.kr",
            'image_url': settings.STATIC_URL + 'images/museum_sema.jpg',
            'region': "seoul",
            'type': "art_museum"
        },
        {
            'id': 5,
            'name': "경기도미술관",
            'address': "경기도 안산시 단원구 동산로 268",
            'phone_number': "031-481-7000",
            'operating_hours': "10:00 - 18:00 (월요일 휴관)",
            'description': "경기도의 대표적인 현대미술관으로, 지역 미술 발전과 소통을 지향합니다.",
            'website': "http://gmoma.ggcf.or.kr/",
            'image_url': settings.STATIC_URL + 'images/museum_gyeonggi.jpg',
            'region': "gyeonggi",
            'type': "art_museum"
        }
    ]
    # [추가 사항] End

    context = {
        'museums_data': json.dumps(museums_data) # JSON 문자열로 변환하여 템플릿에 전달
    }
    return render(request, 'gallery.html', context)
# [수정 사항] End

@require_GET
def archive_view(request):
    return render(request, 'archive.html')

# API 엔드포인트: 이미지 검색 및 필터링
@require_GET
def api_get_images(request):
    search_term = request.GET.get('search')
    selected_style = request.GET.get('style') 
    sort_order = request.GET.get('sort') 

    images = GeneratedImage.objects.all()

    if search_term:
        images = images.filter(
            Q(title__icontains=search_term) |
            Q(description__icontains=search_term) |
            Q(prompt__icontains=search_term)
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

# 주석 처리: 사용하지 않거나 통합된 API 뷰
# @csrf_exempt
# @require_POST
# def delete_conversation_view(request):
#     # ... (기존 코드 유지 또는 주석 처리)
#     pass

# @csrf_exempt
# @require_POST
# def clear_all_history_view(request):
#     # ... (기존 코드 유지 또는 주석 처리)
#     pass

# @csrf_exempt
# @require_POST
# def get_or_create_conversation_view(request):
#     # ... (기존 코드 유지 또는 주석 처리)
#     pass