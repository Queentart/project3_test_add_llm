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
import httpx # requests 대신 httpx 사용 (비동기 및 동기 모두 지원)
import random
import traceback
import logging

logger = logging.getLogger(__name__)

# ComfyUI 관련 설정 (settings.py에서 가져오기, 기본값 지정)
# settings.py에 정의되어 있지 않을 경우 기본값으로 폴백
COMFYUI_API_URL = getattr(settings, 'COMFYUI_API_URL', "http://127.0.0.1:8188/prompt")
COMFYUI_HISTORY_URL = getattr(settings, 'COMFYUI_HISTORY_URL', "http://127.0.0.1:8188/history")
COMFYUI_IMAGE_URL = getattr(settings, 'COMFYUI_IMAGE_URL', "http://127.0.0.1:8188/view")
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', "/tmp/comfyui_input_images") # 실제 ComfyUI input 폴더 경로로 변경 필요

# --- ComfyUI API 관련 헬퍼 함수들 ---

def queue_prompt(client, prompt_data):
    """ComfyUI에 프롬프트 큐를 요청합니다."""
    logger.debug(f"Sending prompt to ComfyUI: {json.dumps(prompt_data, indent=2)}")
    data = {"prompt": prompt_data}
    response = client.post(COMFYUI_API_URL, json=data, timeout=30)
    response.raise_for_status()
    prompt_id = response.json().get("prompt_id")
    logger.debug(f"Received prompt_id: {prompt_id}")
    return prompt_id

def get_history(client, prompt_id):
    """
    지정된 prompt_id에 대한 ComfyUI 작업 이력을 조회합니다.
    ComfyUI의 /history 엔드포인트는 전체 히스토리를 반환하므로,
    여기서 prompt_id를 찾아 파싱합니다.
    """
    url = COMFYUI_HISTORY_URL # 쿼리 파라미터 제거
    
    try:
        response = client.get(url, timeout=30)
        response.raise_for_status()
        full_history = response.json() # 전체 히스토리 데이터
        
        # 제공된 JSON 구조에 따르면 prompt_id가 최상위 키입니다.
        if str(prompt_id) in full_history:
            history_for_prompt = full_history[str(prompt_id)]
            logger.debug(f"Found history for prompt_id {prompt_id}. Status: {history_for_prompt.get('status', {}).get('status_str')}")
            # _perform_image_generation 함수에서 `history_data[prompt_id]`로 접근할 수 있도록
            # {prompt_id: 해당 prompt의 history} 형태로 반환합니다.
            return {str(prompt_id): history_for_prompt}
        else:
            logger.debug(f"No history found for prompt_id {prompt_id} in current ComfyUI history.")
            return {} # 해당 prompt_id의 히스토리가 아직 없으면 빈 딕셔너리 반환
    except httpx.RequestError as e:
        logger.error(f"Failed to get history from ComfyUI: {e}")
        raise # 예외를 다시 발생시켜 상위 호출자에서 처리하도록 함

def get_image(client, filename, subfolder, file_type="output"):
    """ComfyUI에서 생성된 이미지 파일을 다운로드합니다."""
    url = f"{COMFYUI_IMAGE_URL}?filename={filename}&subfolder={subfolder}&type={file_type}"
    logger.debug(f"Attempting to get image from URL: {url}")
    response = client.get(url, timeout=60)
    response.raise_for_status()
    logger.debug(f"Image download successful for {filename}")
    return response.content

# --- 백그라운드 이미지 생성 함수 (메인 스레드에서 분리되어 실행될 것) ---
def _perform_image_generation(task_id, positive_prompt, negative_prompt, uploaded_image_name=None):
    images = [] # <-- 이 줄이 추가되었습니다. (images 변수 초기화)
    try:
        # 캐시 초기 상태 설정
        cache.set(task_id, {"status": "PENDING", "message": "이미지 생성 시작 중...", "progress": 0}, timeout=600)
        logger.info(f"Task {task_id} - ComfyUI 워크플로우를 실행합니다. Prompt: '{positive_prompt[:50]}...', Negative: '{negative_prompt[:50]}...'")
        if uploaded_image_name:
            logger.info(f"Task {task_id} - Using uploaded image: {uploaded_image_name}")

        # === ComfyUI 워크플로우 JSON 정의 ===
        # 이 JSON은 ComfyUI에서 워크플로우를 저장한 JSON을 기반으로 합니다.
        # SaveImage 노드의 ID (여기서는 "8")와 LoadImage 노드의 ID (여기서는 "9")는
        # 여러분의 실제 ComfyUI 워크플로우와 일치해야 합니다.
        # IPAdapter 관련 노드 ID (3, 4, 7)도 마찬가지입니다.
        prompt_json = {
            "1": { "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"}, "class_type": "CheckpointLoaderSimple", "_meta": {"title": "체크포인트 로드"} },
            "2": { "inputs": { "width": 1024, "height": 1024, "batch_size": 1 }, "class_type": "EmptyLatentImage", "_meta": {"title": "빈 잠재 이미지"} },
            "5": { "inputs": { "seed": random.randint(0, 0xFFFFFFFFFFFFFFFF), "steps": 20, "cfg": 8, "sampler_name": "euler", "scheduler": "normal", "denoise": 1 }, "class_type": "KSampler", "_meta": {"title": "KSampler"} },
            "6": { "inputs": { "samples": ["5", 0], "vae": ["1", 2] }, "class_type": "VAEDecode", "_meta": {"title": "VAE 디코드"} },
            "8": { "inputs": { "filename_prefix": "comfyui_generated_image", "images": ["6", 0] }, "class_type": "SaveImage", "_meta": {"title": "이미지 저장"} }, # SaveImage 노드 ID: 8
            "10": { "inputs": { "system_prompt": "superior", "user_prompt": negative_prompt, "clip": ["1", 1] }, "class_type": "CLIPTextEncodeLumina2", "_meta": {"title": "CLIP 텍스트 인코딩 (Lumina2)"} },
            "11": { "inputs": { "system_prompt": "superior", "user_prompt": positive_prompt, "clip": ["1", 1] }, "class_type": "CLIPTextEncodeLumina2", "_meta": {"title": "CLIP 텍스트 인코딩 (Lumina2)"} }
        }

        # IPAdapter를 사용하는 경우 워크플로우에 노드 추가 및 KSampler 모델 변경
        if uploaded_image_name:
            prompt_json["3"] = { "inputs": {"ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"}, "class_type": "IPAdapterModelLoader", "_meta": {"title": "IPAdapter Model Loader"} }
            prompt_json["4"] = { "inputs": {"clip_name": "SDXLopen_clip_pytorch_model_vit_h.safetensors"}, "class_type": "CLIPVisionLoader", "_meta": {"title": "CLIP_VISION 로드"} }
            prompt_json["7"] = { "inputs": { "weight": 1.0, "weight_type": "linear", "combine_embeds": "concat", "start_at": 0, "end_at": 1, "embeds_scaling": "V only", "model": ["1", 0], "ipadapter": ["3", 0], "image": ["9", 0], "attn_mask": ["9", 1], "clip_vision": ["4", 0] }, "class_type": "IPAdapterAdvanced", "_meta": {"title": "IPAdapter Advanced"} }
            prompt_json["9"] = { "inputs": {"image": uploaded_image_name}, "class_type": "LoadImage", "_meta": {"title": "이미지 로드"} } # LoadImage 노드 ID: 9
            prompt_json["5"]["inputs"]["model"] = ["7", 0] # KSampler의 모델을 IPAdapter 출력으로 변경
        else:
            prompt_json["5"]["inputs"]["model"] = ["1", 0] # 텍스트-이미지 생성 시 기본 CheckpointLoaderSimple (ID 1)의 모델 사용

        # KSampler의 positive, negative, latent_image 입력 연결
        prompt_json["5"]["inputs"]["positive"] = ["11", 0]
        prompt_json["5"]["inputs"]["negative"] = ["10", 0]
        prompt_json["5"]["inputs"]["latent_image"] = ["2", 0]

        # === ComfyUI API 호출 및 폴링 ===
        with httpx.Client() as comfyui_client:
            # 1. 프롬프트 큐에 추가
            prompt_id = queue_prompt(comfyui_client, prompt_json)

            if not prompt_id:
                raise Exception("ComfyUI 워크플로우 큐에 실패했습니다. Prompt ID를 받지 못했습니다.")

            cache.set(task_id, {"status": "PROCESSING", "message": f"워크플로우 큐에 추가됨. Prompt ID: {prompt_id}", "progress": 10}, timeout=600)
            logger.info(f"Task {task_id} - 워크플로우가 성공적으로 큐에 추가되었습니다. Prompt ID: {prompt_id}")

            # 2. 이미지 생성 완료까지 폴링
            max_check_attempts = 200 # 2초 * 200 = 400초 (약 6분 40초)
            polling_interval = 2 # 2초 간격 (필요시 3초나 5초로 변경 고려)

            for i in range(max_check_attempts):
                time.sleep(polling_interval) # 다음 시도 전 대기
                
                # 진행률 업데이트 (ComfyUI의 실시간 진행률 API가 없으므로 시간 기반으로 대략 추정)
                progress = min(99, int(((i + 1) / max_check_attempts) * 100))
                cache.set(task_id, {
                    "status": "PROCESSING",
                    "message": f"이미지 생성 진행 중... ({i+1}/{max_check_attempts} 시도 중)",
                    "progress": progress
                }, timeout=600)
                logger.debug(f"Task {task_id} - Attempt {i+1}/{max_check_attempts}: Checking history for prompt_id {prompt_id}... Progress: {progress}%")

                history_data = get_history(comfyui_client, prompt_id) # 수정된 get_history 함수 호출

                # ComfyUI 히스토리에서 해당 prompt_id의 결과를 확인
                if history_data and str(prompt_id) in history_data:
                    prompt_history = history_data[str(prompt_id)]
                    
                    # ComfyUI가 작업 완료를 알리고 outputs가 있는지 확인
                    # ComfyUI의 status 필드는 워크플로우 완료 후에만 신뢰할 수 있습니다.
                    # outputs가 존재하는 것이 더 확실한 완료 신호일 수 있습니다.
                    
                    output_images = [] # 이 변수는 현재 루프에서 사용되지 않으며, images 변수가 이미 위에 초기화되어 있습니다.
                    image_found_in_outputs = False

                    # 'outputs' 키 아래에 노드 ID(예: "8")가 있고, 그 안에 'images' 리스트가 있습니다.
                    if 'outputs' in prompt_history and prompt_history['outputs']:
                        for node_id, node_output in prompt_history['outputs'].items():
                            logger.debug(f"Task {task_id} - Checking node ID: {node_id}, Node output keys: {node_output.keys()}")
                            if node_id == "8" and "images" in node_output: # SaveImage 노드 (ID 8)
                                logger.debug(f"Task {task_id} - Found SaveImage node (ID 8) output.")
                                for img_info in node_output["images"]:
                                    if img_info.get("type") == "output": # 'output' 타입 이미지인지 확인
                                        image_name = img_info["filename"]
                                        image_subfolder = img_info["subfolder"] # 보통 비어있음 ('')
                                        
                                        # Django의 MEDIA_ROOT 아래에 저장할 경로 구성
                                        # settings.MEDIA_ROOT를 "media/comfyui_output/"으로 설정했다면
                                        # output_subfolder_path는 "media/comfyui_output/" + image_subfolder
                                        output_subfolder_path = os.path.join(settings.MEDIA_ROOT, image_subfolder)
                                        os.makedirs(output_subfolder_path, exist_ok=True) # 폴더 없으면 생성
                                        output_full_path = os.path.join(output_subfolder_path, image_name)

                                        try:
                                            logger.info(f"Task {task_id} - Attempting to download image: {image_name} from ComfyUI API.")
                                            image_data = get_image(comfyui_client, image_name, image_subfolder)
                                            if image_data:
                                                with open(output_full_path, 'wb') as f:
                                                    f.write(image_data)
                                                
                                                # 클라이언트에서 접근 가능한 URL 생성
                                                # settings.MEDIA_URL이 '/media/'이고 MEDIA_ROOT가 'BASE_DIR/media/comfyui_output'일 때
                                                # 이미지 URL은 /media/comfyui_output/filename.png 형태가 됩니다.
                                                image_url = f"{settings.MEDIA_URL}{os.path.relpath(output_full_path, settings.MEDIA_ROOT).replace(os.sep, '/')}"
                                                
                                                images.append({"name": image_name, "url": image_url}) # images 리스트에 추가
                                                logger.info(f"Task {task_id} - Image saved locally and URL generated: {image_url}")
                                                image_found_in_outputs = True # 이미지를 하나라도 성공적으로 찾고 저장함
                                            else:
                                                logger.error(f"Task {task_id} - No image data received for {image_name} from ComfyUI.")
                                        except httpx.HTTPStatusError as e:
                                            logger.error(f"Task {task_id} - HTTP error downloading image {image_name}: {e.response.status_code} - {e.response.text}")
                                            logger.error(f"ComfyUI API response on image download error: {e.response.text}") # ComfyUI의 에러 응답 전문
                                        except Exception as e:
                                            logger.error(f"Task {task_id} - Unexpected error saving image {image_name} locally: {e}")
                                            traceback.print_exc() # 스택 트레이스 출력
                        
                        if image_found_in_outputs: # 이미지가 하나라도 성공적으로 처리되었다면
                            cache.set(task_id, {
                                "status": "SUCCESS",
                                "message": "이미지 생성이 완료되었습니다!",
                                "images": images, # 이미지 URL 리스트 포함하여 캐시에 저장
                                "progress": 100
                            }, timeout=600)
                            logger.info(f"Task {task_id} - IMAGE GENERATION SUCCESS. Final URLs: {images}")
                            return # 성공했으니 함수 종료

                        else:
                            logger.warning(f"Task {task_id} - History found for prompt_id {prompt_id} but no valid images from SaveImage node (ID 8) yet or image download/save failed. Continuing polling.")

                    # outputs는 있지만 아직 images가 없거나, status가 completed 되지 않은 경우 계속 진행
                    else:
                        logger.debug(f"Task {task_id} - History found for prompt_id {prompt_id} but 'outputs' key not found or empty. Current history state: {prompt_history.keys()}")

                else:
                    logger.debug(f"Task {task_id} - History data for prompt_id {prompt_id} not yet available in ComfyUI history cache.")

            # 3. 최대 시도 횟수를 초과한 경우 (시간 초과)
            cache.set(task_id, {
                "status": "FAILED",
                "message": "이미지 생성 시간 초과: ComfyUI 응답이 없거나 작업이 완료되지 않았습니다. ComfyUI 로그를 확인하세요.",
                "progress": 100
            }, timeout=600)
            logger.error(f"Task {task_id} - 이미지 생성 시간 초과: {max_check_attempts} 시도 후에도 이미지 결과를 받지 못함.")

    except httpx.RequestError as e:
        error_message = f"ComfyUI 서버 통신 오류: {e}"
        traceback.print_exc()
        cache.set(task_id, {
            "status": "FAILED",
            "message": f"ComfyUI 서버와 통신 중 오류 발생: {error_message}",
            "details": traceback.format_exc(),
            "progress": 100
        }, timeout=600)
        logger.critical(f"Task {task_id} - {error_message}")
    except httpx.HTTPStatusError as e:
        error_message = f"ComfyUI API 오류 (HTTP {e.response.status_code}): {e.response.text}"
        traceback.print_exc()
        cache.set(task_id, {
            "status": "FAILED",
            "message": f"ComfyUI API 요청 오류 발생: {error_message}",
            "details": traceback.format_exc(),
            "progress": 100
        }, timeout=600)
        logger.critical(f"Task {task_id} - {error_message}")
    except Exception as e:
        error_message = f"백그라운드 이미지 생성 중 예상치 못한 오류 발생: {str(e)}"
        traceback.print_exc()
        cache.set(task_id, {
            "status": "FAILED",
            "message": f"이미지 생성 중 예상치 못한 오류가 발생했습니다: {str(e)}",
            "details": traceback.format_exc(),
            "progress": 100
        }, timeout=600)
        logger.critical(f"Task {task_id} - {error_message}")


@csrf_exempt
@require_POST
def generate_image_view(request):
    try:
        user_positive_prompt = request.POST.get('prompt', '').strip()
        # 부정 프롬프트 기본값 강화
        user_negative_prompt = request.POST.get('negative_prompt',
            "Cartoonish, chibi, overly simplistic, unrealistic proportions, child-like drawing, sketchy lines, rough edges, pixelated, low quality, blurry, distorted, Multiple characters, crowded background, distracting elements, too busy, ugly background, deformed hands, extra limbs, disfigured face, unnatural pose."
        ).strip()
        uploaded_image_file = request.FILES.get('input_image')
        uploaded_image_name = None

        if uploaded_image_file:
            comfyui_input_dir = COMFYUI_INPUT_DIR
            os.makedirs(comfyui_input_dir, exist_ok=True) # ComfyUI의 input 디렉토리 생성 확인

            fs = FileSystemStorage(location=comfyui_input_dir)
            ext = os.path.splitext(uploaded_image_file.name)[1]
            unique_filename = f"{uuid.uuid4().hex}{ext}"
            
            uploaded_filename = fs.save(unique_filename, uploaded_image_file)
            uploaded_image_name = uploaded_filename # ComfyUI 워크플로우에서 사용할 파일명
            logger.info(f"Uploaded image saved to ComfyUI input directory: {os.path.join(comfyui_input_dir, uploaded_filename)}")
        else:
            logger.info("No image file uploaded. Proceeding with text-to-image generation.")

        if not user_positive_prompt:
            return JsonResponse({"status": "error", "message": "긍정 프롬프트는 필수입니다."}, status=400)

        task_id = str(uuid.uuid4()) # 고유한 작업 ID 생성

        # 백그라운드 스레드에서 이미지 생성 함수 실행
        # 스레드 이름 지정 (선택 사항이지만 디버깅에 유용)
        thread = threading.Thread(
            target=_perform_image_generation, 
            args=(task_id, user_positive_prompt, user_negative_prompt, uploaded_image_name),
            name=f"ImageGenTask-{task_id}"
        )
        thread.daemon = True # 메인 스레드 종료 시 서브 스레드도 종료
        thread.start()

        return JsonResponse({
            "status": "accepted",
            "message": "이미지 생성 요청이 접수되었습니다. 잠시 후 상태를 조회해 주세요.",
            "task_id": task_id
        }, status=202) # 202 Accepted 응답

    except Exception as e:
        logger.exception("Django View Error in generate_image_view:") # 오류 발생 시 스택 트레이스 포함
        return JsonResponse({"status": "error", "message": f"서버 처리 중 알 수 없는 오류가 발생했습니다: {str(e)}"}, status=500)

@csrf_exempt
@require_GET
def check_image_status_view(request, task_id):
    """클라이언트가 이미지 생성 작업의 상태를 조회하는 API 엔드포인트."""
    status_data = cache.get(task_id) # 캐시에서 작업 상태 조회
    if status_data:
        logger.debug(f"Status check for task {task_id}: {status_data}")
        return JsonResponse(status_data)
    else:
        logger.info(f"Task {task_id} not found in cache or expired.")
        return JsonResponse({
            "status": "NOT_FOUND",
            "message": "해당 Task ID를 찾을 수 없거나 만료되었습니다. 다시 시도해 주세요."
        }, status=404)