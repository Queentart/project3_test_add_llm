import traceback
import time
import json
import os
import requests
import base64
import uuid
import logging
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

# JSON 파일들이 위치한 디렉토리 경로 (프로젝트 루트 기준으로 설정)
BASE_DIR = settings.BASE_DIR
JSON_DEFINITIONS_DIR = os.path.join(BASE_DIR, 'comfyui_workflows')

# ComfyUI API 호출 설정
COMFYUI_API_URL = settings.COMFYUI_API_URL
COMFYUI_HISTORY_URL = settings.COMFYUI_HISTORY_URL
COMFYUI_IMAGE_URL = settings.COMFYUI_IMAGE_URL
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', os.path.join(settings.BASE_DIR, 'comfyui_data', 'input'))


def load_json_config(file_name: str) -> dict:
    """
    지정된 JSON 설정 파일을 로드합니다.
    """
    file_path = os.path.join(JSON_DEFINITIONS_DIR, file_name)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON config file not found: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_image_based_on_json_logic(
    prompt_en: str,
    logic_type: str, # 'text_to_image' 또는 'image_to_image'
    negative_prompt_en: str = "",
    image_path_for_i2i: str = None # I2I를 위한 이미지 파일 경로 (views.py에서 넘어옴)
) -> str:
    """
    ComfyUI JSON 워크플로우를 기반으로 이미지를 생성하고 결과 이미지 URL을 반환합니다.
    """
    try:
        # 1. logic_type에 따라 적절한 워크플로우 JSON 파일 로드
        workflow_file_name = ""
        if logic_type == 'text_to_image':
            workflow_file_name = 'text_to_image.json' # 제공된 T2I JSON 파일 이름
        elif logic_type == 'image_to_image':
            workflow_file_name = 'i2i_controlnet.json' # 제공된 I2I JSON 파일 이름
            if not image_path_for_i2i or not os.path.exists(image_path_for_i2i):
                raise ValueError("Image file path is required for image_to_image generation and must exist.")
        else:
            raise ValueError(f"Unsupported logic_type: {logic_type}")

        workflow_json = load_json_config(workflow_file_name)['prompt'] # 'prompt' 키 안의 실제 워크플로우 부분만 사용

        # 2. 프롬프트 주입: 노드 ID를 명시적으로 지정
        # 새롭게 추가된 변수: positive_prompt_node_id
        # 새롭게 추가된 변수: negative_prompt_node_id
        # 새롭게 추가된 변수: image_load_node_id

        # T2I와 I2I 워크플로우에 따라 노드 ID를 다르게 지정
        if logic_type == 'text_to_image':
            positive_prompt_node_id = '6' # text_to_image.json의 긍정 프롬프트 노드 ID
            negative_prompt_node_id = '7' # text_to_image.json의 부정 프롬프트 노드 ID
            image_load_node_id = None # T2I에서는 이미지 로드 노드 없음
        elif logic_type == 'image_to_image':
            positive_prompt_node_id = '10' # i2i_controlnet.json의 긍정 프롬프트 노드 ID
            negative_prompt_node_id = '11' # i2i_controlnet.json의 부정 프롬프트 노드 ID
            image_load_node_id = '2' # i2i_controlnet.json의 이미지 로드 노드 ID

        if positive_prompt_node_id and positive_prompt_node_id in workflow_json:
            workflow_json[positive_prompt_node_id]['inputs']['text'] = prompt_en
        else:
            logger.warning(f"Positive prompt node (ID: {positive_prompt_node_id}) not found or invalid for {logic_type}. Image generation might fail or use default prompt.")

        if negative_prompt_node_id and negative_prompt_node_id in workflow_json and negative_prompt_en:
            workflow_json[negative_prompt_node_id]['inputs']['text'] = negative_prompt_en
        # else:
            # logger.info("Negative prompt node not found or negative prompt is empty. Skipping negative prompt insertion.")

        # 3. I2I 이미지 파일 처리: Load Image 노드에 파일 이름 주입 및 ComfyUI input 디렉토리로 복사
        if logic_type == 'image_to_image' and image_load_node_id and image_path_for_i2i:
            if image_load_node_id in workflow_json:
                # 원본 파일명 추출 및 ComfyUI 입력 디렉토리에 저장
                file_extension = os.path.splitext(os.path.basename(image_path_for_i2i))[1]
                # 새롭게 추가된 변수: unique_filename
                unique_filename = f"{uuid.uuid4()}{file_extension}" # 고유한 파일명 생성
                comfy_input_filename = unique_filename # ComfyUI에서 로드할 파일명

                # 새롭게 추가된 변수: destination_path
                destination_path = os.path.join(COMFYUI_INPUT_DIR, comfy_input_filename)
                try:
                    # 파일을 직접 복사 (default_storage.path()로 얻은 실제 파일 경로를 사용)
                    # logger.debug(f"Attempting to copy from {image_path_for_i2i} to {destination_path}")
                    with open(image_path_for_i2i, 'rb') as src_file:
                        with open(destination_path, 'wb') as dest_file:
                            dest_file.write(src_file.read())
                    logger.info(f"Image copied to ComfyUI input directory: {destination_path}")

                    # Load Image 노드의 'image' 필드에 파일명 주입
                    workflow_json[image_load_node_id]['inputs']['image'] = comfy_input_filename
                    logger.debug(f"Set LoadImage node {image_load_node_id} image input to {comfy_input_filename}")
                except Exception as e:
                    logger.error(f"Error copying image to ComfyUI input directory or updating workflow: {e}")
                    raise
            else:
                logger.warning(f"LoadImage node (ID: {image_load_node_id}) not found in image_to_image workflow.")

        # 4. ComfyUI API 호출
        client_id = str(uuid.uuid4()) # 고유한 클라이언트 ID 생성
        payload = {
            "prompt": workflow_json,
            "client_id": client_id
        }

        # logger.debug(f"Sending payload to ComfyUI: {json.dumps(payload, indent=2)}")

        response = requests.post(COMFYUI_API_URL, json=payload, timeout=300) # 타임아웃 5분
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생

        response_data = response.json()
        prompt_id = response_data.get('prompt_id')

        if not prompt_id:
            raise ValueError("ComfyUI did not return a prompt_id.")

        # 5. 생성된 이미지 URL 가져오기 (히스토리 API 폴링)
        # ComfyUI가 비동기적으로 이미지를 생성하므로, 완료될 때까지 히스토리 API를 폴링
        max_attempts = 60 # 최대 60번 시도 (3초 간격이면 3분)
        current_attempt = 0
        generated_image_info = None

        while current_attempt < max_attempts:
            current_attempt += 1
            history_response = requests.get(f"{COMFYUI_HISTORY_URL}?client_id={client_id}", timeout=30)
            history_response.raise_for_status()
            history_data = history_response.json()

            if prompt_id in history_data.get('history', {}):
                outputs = history_data['history'][prompt_id].get('outputs', {})
                for node_id, node_output in outputs.items():
                    if 'images' in node_output:
                        generated_image_info = node_output['images'][0] # 첫 번째 이미지 가져오기
                        break
                if generated_image_info:
                    break # 이미지 정보 찾았으면 루프 종료

            time.sleep(3) # 3초 대기 후 재시도

        if not generated_image_info:
            raise TimeoutError(f"Image generation timed out after {max_attempts} attempts.")

        filename = generated_image_info['filename']
        subfolder = generated_image_info['subfolder']
        file_type = generated_image_info['type'] # 'output' 또는 'temp'

        # ComfyUI의 /view 엔드포인트를 통해 이미지 URL 생성
        image_url = f"{COMFYUI_IMAGE_URL}?filename={filename}&subfolder={subfolder}&type={file_type}"
        return image_url

    except FileNotFoundError as e:
        logger.error(f"JSON config file error: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to ComfyUI API: {e}")
        raise
    except ValueError as e:
        logger.error(f"Value error in image generation logic: {e}")
        raise
    except TimeoutError as e:
        logger.error(f"ComfyUI image generation polling timed out: {e}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during image generation: {e}\n{traceback.format_exc()}")
        raise