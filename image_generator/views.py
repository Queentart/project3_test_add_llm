# image_generator/views.py

import threading
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.core.cache import cache
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
import json
import time
import httpx
import random
import traceback

# ComfyUI 관련 설정 (settings.py에서 가져오기)
COMFYUI_API_URL = getattr(settings, 'COMFYUI_API_URL')
COMFYUI_HISTORY_URL = getattr(settings, 'COMFYUI_HISTORY_URL')
COMFYUI_IMAGE_URL = getattr(settings, 'COMFYUI_IMAGE_URL')
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR')

# --- ComfyUI API 관련 헬퍼 함수들 ---

def queue_prompt(client, prompt_data):
    """ComfyUI에 프롬프트 큐를 요청합니다."""
    data = {"prompt": prompt_data}
    response = client.post(COMFYUI_API_URL, json=data, timeout=30) # 요청 타임아웃 30초 설정
    response.raise_for_status() # 4xx, 5xx 에러 발생 시 예외 처리
    return response.json().get("prompt_id")

def get_history(client, prompt_id):
    """지정된 prompt_id에 대한 ComfyUI 작업 이력을 조회합니다."""
    url = f"{COMFYUI_HISTORY_URL}?prompt={prompt_id}"
    response = client.get(url, timeout=30) # 요청 타임아웃 30초 설정
    response.raise_for_status()
    return response.json().get("history", {})

def get_image(client, filename, subfolder, file_type="output"):
    """ComfyUI에서 생성된 이미지 파일을 다운로드합니다."""
    url = f"{COMFYUI_IMAGE_URL}?filename={filename}&subfolder={subfolder}&type={file_type}"
    response = client.get(url, timeout=60) # 이미지 다운로드 타임아웃 60초 설정
    response.raise_for_status()
    return response.content

# --- 백그라운드 이미지 생성 함수 (메인 스레드에서 분리되어 실행될 것) ---
def _perform_image_generation(task_id, positive_prompt, negative_prompt, uploaded_image_name=None):
    try:
        cache.set(task_id, {"status": "PENDING", "message": "이미지 생성 시작 중...", "progress": 0}, timeout=600)
        print(f"DEBUG: Task {task_id} - ComfyUI 워크플로우를 실행합니다...")

        # --- ComfyUI 워크플로우 JSON 정의 (업로드 이미지 유무에 따라 동적 구성) ---
        prompt_json = {
            "1": { # Checkpoint Loader Simple
                "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
                "class_type": "CheckpointLoaderSimple",
                "_meta": {"title": "체크포인트 로드"}
            },
            "2": { # Empty Latent Image
                "inputs": {
                    "width": 1024,
                    "height": 1024,
                    "batch_size": 1
                },
                "class_type": "EmptyLatentImage",
                "_meta": {"title": "빈 잠재 이미지"}
            },
            "5": { # KSampler
                "inputs": {
                    "seed": random.randint(0, 0xFFFFFFFFFFFFFFFF),
                    "steps": 20,
                    "cfg": 8,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                },
                "class_type": "KSampler",
                "_meta": {"title": "KSampler"}
            },
            "6": { # VAE Decode
                "inputs": {
                    "samples": ["5", 0],
                    "vae": ["1", 2]
                },
                "class_type": "VAEDecode",
                "_meta": {"title": "VAE 디코드"}
            },
            "8": { # Save Image
                "inputs": {
                    "filename_prefix": "comfyui_generated_image",
                    "images": ["6", 0]
                },
                "class_type": "SaveImage",
                "_meta": {"title": "이미지 저장"}
            },
            "10": { # CLIP Text Encode (Negative Prompt)
                "inputs": {
                    "system_prompt": "superior",
                    "user_prompt": negative_prompt,
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncodeLumina2",
                "_meta": {"title": "CLIP 텍스트 인코딩 (Lumina2)"}
            },
            "11": { # CLIP Text Encode (Positive Prompt)
                "inputs": {
                    "system_prompt": "superior",
                    "user_prompt": positive_prompt,
                    "clip": ["1", 1]
                },
                "class_type": "CLIPTextEncodeLumina2",
                "_meta": {"title": "CLIP 텍스트 인코딩 (Lumina2)"}
            }
        }

        # IPAdapter 워크플로우 추가 (업로드된 이미지가 있을 경우)
        if uploaded_image_name:
            prompt_json["3"] = { # IPAdapter Model Loader
                "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"},
                "class_type": "IPAdapterModelLoader",
                "_meta": {"title": "IPAdapter Model Loader"}
            }
            prompt_json["4"] = { # CLIPVision Loader
                "inputs": {"clip_name": "SDXLopen_clip_pytorch_model_vit_h.safetensors"},
                "class_type": "CLIPVisionLoader",
                "_meta": {"title": "CLIP_VISION 로드"}
            }
            prompt_json["7"] = { # IPAdapter Advanced
                "inputs": {
                    "weight": 1.0, # IPAdapter 가중치 (필요시 조절)
                    "weight_type": "linear",
                    "combine_embeds": "concat",
                    "start_at": 0,
                    "end_at": 1,
                    "embeds_scaling": "V only",
                    "model": ["1", 0],
                    "ipadapter": ["3", 0],
                    "image": ["9", 0],
                    "attn_mask": ["9", 1],
                    "clip_vision": ["4", 0]
                },
                "class_type": "IPAdapterAdvanced",
                "_meta": {"title": "IPAdapter Advanced"}
            }
            prompt_json["9"] = { # Load Image (업로드된 이미지가 들어갈 노드)
                "inputs": {"image": uploaded_image_name}, # JSON에 맞춰 'image' 필드 사용
                "class_type": "LoadImage",
                "_meta": {"title": "이미지 로드"}
            }
            prompt_json["5"]["inputs"]["model"] = ["7", 0] # KSampler 모델 입력을 IPAdapter 노드와 연결
        else:
            prompt_json["5"]["inputs"]["model"] = ["1", 0] # IPAdapter 없는 경우 CheckpointLoader와 직접 연결

        # KSampler의 나머지 입력 연결
        prompt_json["5"]["inputs"]["positive"] = ["11", 0]
        prompt_json["5"]["inputs"]["negative"] = ["10", 0]
        prompt_json["5"]["inputs"]["latent_image"] = ["2", 0]

        # --- ComfyUI API 호출 ---
        with httpx.Client() as comfyui_client:
            prompt_id = queue_prompt(comfyui_client, prompt_json)

            if not prompt_id:
                raise Exception("ComfyUI 워크플로우 큐에 실패했습니다. Prompt ID를 받지 못했습니다.")

            cache.set(task_id, {"status": "PROCESSING", "message": f"워크플로우 큐에 추가됨. Prompt ID: {prompt_id}", "progress": 10}, timeout=600)
            print(f"DEBUG: Task {task_id} - 워크플로우가 성공적으로 큐에 추가되었습니다. Prompt ID: {prompt_id}")

            max_check_attempts = 120 # 2초 * 120 = 4분 동안 시도 (ComfyUI 작업 시간에 따라 조절)
            for i in range(max_check_attempts):
                time.sleep(2) # 2초마다 상태 확인 (너무 자주 체크하면 ComfyUI 부하 증가)
                history_data = get_history(comfyui_client, prompt_id)

                # ComfyUI 작업이 완료되었는지 확인 (prompt_id가 history_data에 있고, outputs가 비어있지 않은지)
                # 'status' 필드는 현재 API에서 직접 제공되지 않아 history 존재 여부로 판단
                if history_data and prompt_id in history_data and history_data[prompt_id].get("outputs"):
                    outputs = history_data[prompt_id]["outputs"]
                    images = []
                    for node_id, node_output in outputs.items():
                        # 'SaveImage' 노드의 ID를 확인 (여기서는 8번 노드)
                        if node_id == "8" and "images" in node_output:
                            for img_info in node_output["images"]:
                                if img_info.get("type") == "output": # 'output' 타입 이미지인지 확인
                                    image_name = img_info["filename"]
                                    image_subfolder = img_info["subfolder"]
                                    
                                    # ComfyUI 출력 이미지를 Django MEDIA_ROOT에 저장
                                    # 이 경로에 저장된 이미지는 웹에서 접근 가능합니다.
                                    output_subfolder_path = os.path.join(settings.MEDIA_ROOT, 'comfyui_output', image_subfolder)
                                    os.makedirs(output_subfolder_path, exist_ok=True)
                                    output_full_path = os.path.join(output_subfolder_path, image_name)

                                    # 이미지 데이터 가져오기
                                    try:
                                        image_data = get_image(comfyui_client, image_name, image_subfolder)
                                        if image_data:
                                            with open(output_full_path, 'wb') as f:
                                                f.write(image_data)
                                            
                                            # 클라이언트에서 접근할 수 있는 URL 생성
                                            # settings.MEDIA_URL은 /media/ 로 설정되어 있어야 합니다.
                                            image_url = f"{settings.MEDIA_URL}comfyui_output/{image_subfolder}/{image_name}"
                                            images.append({"name": image_name, "url": image_url})
                                            print(f"DEBUG: Task {task_id} - 이미지 저장 및 URL 생성 완료: {image_url}")
                                        else:
                                            print(f"ERROR: Task {task_id} - 이미지 데이터를 가져오지 못했습니다. 파일명: {image_name}")
                                    except httpx.HTTPStatusError as e:
                                        print(f"ERROR: Task {task_id} - 이미지 다운로드 중 HTTP 오류 발생: {e}")
                                    except Exception as e:
                                        print(f"ERROR: Task {task_id} - 이미지 저장 중 예상치 못한 오류 발생: {e}")

                    if images:
                        cache.set(task_id, {
                            "status": "SUCCESS",
                            "message": "이미지 생성이 완료되었습니다! (이미지 출력)", # 완료 메시지 변경
                            "images": images, # 이미지 URL 리스트 포함
                            "progress": 100
                        }, timeout=600)
                        print(f"DEBUG: Task {task_id} - 이미지 생성 성공 및 캐시 업데이트 완료.")
                        return # 성공했으니 함수 종료

                # 진행률 업데이트 (ComfyUI의 실시간 진행률 API가 없으므로 시간 기반으로 대략 추정)
                progress = min(99, (i + 1) * (99 // max_check_attempts)) # 99%까지 진행
                cache.set(task_id, {
                    "status": "PROCESSING",
                    "message": f"이미지 생성 진행 중... ({i+1}/{max_check_attempts} 시도)",
                    "progress": progress
                }, timeout=600)
                print(f"DEBUG: Task {task_id} - Attempt {i+1}/{max_check_attempts}: Checking history for prompt_id {prompt_id}...")

            # 최대 시도 횟수를 초과한 경우
            cache.set(task_id, {
                "status": "FAILED",
                "message": "이미지 생성 시간 초과: ComfyUI 응답이 없거나 작업이 완료되지 않았습니다.",
                "progress": 100
            }, timeout=600)
            print(f"ERROR: Task {task_id} - 이미지 생성 시간 초과.")

    except httpx.RequestError as e:
        error_message = f"ComfyUI 서버 통신 오류: {e}"
        traceback.print_exc()
        cache.set(task_id, {
            "status": "FAILED",
            "message": f"ComfyUI 서버와 통신 중 오류 발생: {error_message}",
            "details": traceback.format_exc(),
            "progress": 100
        }, timeout=600)
        print(f"ERROR: Task {task_id} - {error_message}")
    except httpx.HTTPStatusError as e:
        error_message = f"ComfyUI API 오류 (HTTP {e.response.status_code}): {e.response.text}"
        traceback.print_exc()
        cache.set(task_id, {
            "status": "FAILED",
            "message": f"ComfyUI API 요청 오류 발생: {error_message}",
            "details": traceback.format_exc(),
            "progress": 100
        }, timeout=600)
        print(f"ERROR: Task {task_id} - {error_message}")
    except Exception as e:
        error_message = f"백그라운드 이미지 생성 중 예상치 못한 오류 발생: {str(e)}"
        traceback.print_exc()
        cache.set(task_id, {
            "status": "FAILED",
            "message": f"이미지 생성 중 예상치 못한 오류가 발생했습니다: {str(e)}",
            "details": traceback.format_exc(),
            "progress": 100
        }, timeout=600)
        print(f"ERROR: Task {task_id} - {error_message}")


@csrf_exempt
@require_POST
def generate_image_view(request):
    try:
        user_positive_prompt = request.POST.get('prompt', '').strip()
        user_negative_prompt = request.POST.get('negative_prompt',
            "Cartoonish, chibi, overly simplistic, unrealistic proportions, child-like drawing, sketchy lines, rough edges, pixelated, low quality, blurry, distorted, Multiple characters, crowded background, distracting elements, too busy, ugly background, deformed hands, extra limbs, disfigured face, unnatural pose."
        ).strip() # 기본 부정 프롬프트도 설정 가능
        uploaded_image_file = request.FILES.get('input_image')
        uploaded_image_name = None

        if uploaded_image_file:
            comfyui_input_dir = COMFYUI_INPUT_DIR
            os.makedirs(comfyui_input_dir, exist_ok=True)

            fs = FileSystemStorage(location=comfyui_input_dir)
            ext = os.path.splitext(uploaded_image_file.name)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            
            uploaded_filename = fs.save(unique_filename, uploaded_image_file)
            uploaded_image_name = uploaded_filename
            print(f"Uploaded image saved to: {os.path.join(comfyui_input_dir, uploaded_filename)}")
        else:
            print("Info: No image file uploaded. Proceeding with text-to-image generation.")

        if not user_positive_prompt:
            return JsonResponse({"status": "error", "message": "긍정 프롬프트는 필수입니다."}, status=400)

        task_id = str(uuid.uuid4())

        thread = threading.Thread(target=_perform_image_generation, args=(task_id, user_positive_prompt, user_negative_prompt, uploaded_image_name))
        thread.daemon = True
        thread.start()

        return JsonResponse({
            "status": "accepted",
            "message": "이미지 생성 요청이 접수되었습니다. 잠시 후 상태를 조회해 주세요.",
            "task_id": task_id
        }, status=202)

    except Exception as e:
        print(f"Django View Error: {e}")
        traceback.print_exc()
        return JsonResponse({"status": "error", "message": f"서버 처리 중 알 수 없는 오류가 발생했습니다: {str(e)}"}, status=500)

@csrf_exempt
@require_GET
def check_image_status_view(request, task_id):
    status_data = cache.get(task_id)
    if status_data:
        return JsonResponse(status_data)
    else:
        return JsonResponse({
            "status": "NOT_FOUND",
            "message": "해당 Task ID를 찾을 수 없거나 만료되었습니다. 다시 시도해 주세요."
        }, status=404)