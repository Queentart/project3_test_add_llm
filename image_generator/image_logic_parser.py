import json
import time
import httpx
import random
import traceback
import logging
import os
import uuid # uuid 모듈 임포트 추가
import base64 # Base64 인코딩/디코딩을 위해 임포트
from django.conf import settings # settings를 참조하기 위해 추가
import asyncio # asyncio를 사용하고 있습니다.
from django.core.files.base import ContentFile # 파일을 저장하기 위해 임포트
from django.core.files.storage import default_storage # Django 스토리지 사용을 위해 임포트

# negative_prompts.py에서 NEGATIVE_PROMPT_MAP 임포트
from llm_cores.negative_prompts import NEGATIVE_PROMPT_MAP
# positive_prompts.py에서 POSITIVE_PROMPT_MAP 임포트
from llm_cores.positive_prompts import POSITIVE_PROMPT_MAP

logger = logging.getLogger(__name__)

# JSON 파일들이 위치한 디렉토리 경로 (프로젝트 루트 기준으로 설정)
BASE_DIR = settings.BASE_DIR
JSON_DEFINITIONS_DIR = os.path.join(BASE_DIR, 'comfyui_workflows')

# ComfyUI API 호출 설정 (settings에서 직접 가져옴)
COMFYUI_API_URL = settings.COMFYUI_API_URL
COMFYUI_HISTORY_URL = settings.COMFYUI_HISTORY_URL
COMFYUI_IMAGE_URL = settings.COMFYUI_IMAGE_URL
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', os.path.join(settings.MEDIA_ROOT, 'comfyui_input'))


# ComfyUI에 요청을 보내는 비동기 함수
async def queue_prompt(prompt_workflow):
    """
    ComfyUI에 워크플로우 프롬프트를 큐에 추가합니다.
    """
    uri = f"{COMFYUI_API_URL}/prompt"
    logger.info(f"Sending prompt to ComfyUI: {uri}")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(uri, json=prompt_workflow)
            response.raise_for_status()  # HTTP 오류가 발생하면 예외 발생
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"ComfyUI API request failed: {e}", exc_info=True)
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response from ComfyUI: {e}", exc_info=True)
        raise

async def get_history(prompt_id):
    """
    ComfyUI에서 특정 prompt_id에 대한 히스토리를 가져옵니다.
    """
    uri = f"{COMFYUI_HISTORY_URL}/{prompt_id}"
    logger.info(f"Fetching history from ComfyUI: {uri}")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(uri)
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        logger.error(f"ComfyUI history request failed: {e}", exc_info=True)
        raise

async def get_image(filename, subfolder, folder_type):
    """
    ComfyUI로부터 이미지를 다운로드합니다.
    """
    uri = f"{COMFYUI_IMAGE_URL}/{filename}?subfolder={subfolder}&type={folder_type}"
    logger.info(f"Downloading image from ComfyUI: {uri}")
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(uri)
            response.raise_for_status()
            return response.content
    except httpx.RequestError as e:
        logger.error(f"ComfyUI image download failed: {e}", exc_info=True)
        raise


async def generate_image_based_on_json_logic(
    workflow_json_filename: str,
    user_prompt: str,
    user_negative_prompt: str,
    image_base64: str = None, # i2i를 위한 base64 인코딩된 이미지 데이터
    denoising_strength: float = 0.7, # i2i를 위한 denoising_strength (0.0~1.0)
    image_width: int = 1024,
    image_height: int = 1024,
    model_name: str = "sd_xl_base_1.0.safetensors",
    lora_model_name: str = None, # LoRA 모델 파일 이름
    lora_strength_model: float = 1.0, # LoRA 모델 적용 강도
    lora_strength_clip: float = 1.0, # LoRA CLIP 적용 강도
    seed: int = None, # 시드 값
    positive_prompt_categories: list = None, # 추가: 긍정 프롬프트 카테고리 리스트
    negative_prompt_categories: list = None # 추가: 부정 프롬프트 카테고리 리스트
) -> dict:
    """
    지정된 JSON 워크플로우 파일을 기반으로 ComfyUI를 통해 이미지를 생성합니다.

    Args:
        workflow_json_filename (str): 사용할 ComfyUI 워크플로우 JSON 파일명 (예: "txt2img_api_workflow.json").
        user_prompt (str): 사용자 입력 긍정 프롬프트.
        user_negative_prompt (str): 사용자 입력 부정 프롬프트.
        image_base64 (str, optional): Base64 인코딩된 이미지 데이터. i2i의 경우에만 필요. Defaults to None.
        denoising_strength (float, optional): i2i 노이즈 제거 강도. Defaults to 0.7.
        image_width (int, optional): 생성할 이미지의 가로 길이. Defaults to 1024.
        image_height (int, optional): 생성할 이미지의 세로 길이. Defaults to 1024.
        model_name (str, optional): 사용할 모델 파일 이름. Defaults to "sd_xl_base_1.0.safetensors".
        lora_model_name (str, optional): 사용할 LoRA 모델 파일 이름. Defaults to None.
        lora_strength_model (float, optional): LoRA 모델 적용 강도. Defaults to 1.0.
        lora_strength_clip (float, optional): LoRA CLIP 적용 강도. Defaults to 1.0.
        seed (int, optional): 이미지 생성에 사용할 시드 값. Defaults to None (랜덤 시드).
        positive_prompt_categories (list, optional): 적용할 긍정 프롬프트 카테고리 리스트. Defaults to None.
        negative_prompt_categories (list, optional): 적용할 부정 프롬프트 카테고리 리스트. Defaults to None.

    Returns:
        dict: 생성된 이미지 파일 경로와 ComfyUI에서 제공하는 이미지 URL을 포함하는 딕셔너리.
    """
    logger.info(f"Starting image generation with workflow: {workflow_json_filename}")

    # 시드 값이 제공되지 않으면 랜덤 시드 생성
    if seed is None:
        seed = random.randint(0, 2**32 - 1)
        logger.info(f"Using random seed: {seed}")
    else:
        logger.info(f"Using provided seed: {seed}")

    try:
        # JSON 워크플로우 파일 로드
        workflow_path = os.path.join(JSON_DEFINITIONS_DIR, workflow_json_filename)
        with open(workflow_path, 'r', encoding='utf-8') as f:
            prompt_workflow = json.load(f)

        # -------------------------------------------------------------
        # [수정 시작] 프롬프트 텍스트 및 카테고리 기반 프롬프트 조합 로직
        # -------------------------------------------------------------
        # 긍정 프롬프트 조합
        combined_positive_prompt = user_prompt
        if positive_prompt_categories:
            for category in positive_prompt_categories:
                if category in POSITIVE_PROMPT_MAP:
                    combined_positive_prompt += f", {POSITIVE_PROMPT_MAP[category]}"
                else:
                    logger.warning(f"Unknown positive prompt category: {category}")
        logger.info(f"Final combined positive prompt: {combined_positive_prompt}")

        # 부정 프롬프트 조합
        combined_negative_prompt = user_negative_prompt
        if negative_prompt_categories:
            for category in negative_prompt_categories:
                if category in NEGATIVE_PROMPT_MAP:
                    combined_negative_prompt += f", {NEGATIVE_PROMPT_MAP[category]}"
                else:
                    logger.warning(f"Unknown negative prompt category: {category}")
        logger.info(f"Final combined negative prompt: {combined_negative_prompt}")

        # ComfyUI 워크플로우 JSON 업데이트
        # 텍스트 프롬프트 업데이트 (6번 노드)
        # ComfyUI의 기본 텍스트 인코딩 노드 ID가 6이라고 가정
        if "6" in prompt_workflow["nodes"]:
            prompt_workflow["nodes"]["6"]["inputs"]["text"] = combined_positive_prompt
            logger.debug(f"Positive prompt node 6 updated with: {combined_positive_prompt}")
        else:
            logger.warning("Node 6 (positive prompt) not found in workflow. Skipping positive prompt update.")

        # 부정 텍스트 프롬프트 업데이트 (7번 노드)
        # ComfyUI의 기본 부정 텍스트 인코딩 노드 ID가 7이라고 가정
        if "7" in prompt_workflow["nodes"]:
            prompt_workflow["nodes"]["7"]["inputs"]["text"] = combined_negative_prompt
            logger.debug(f"Negative prompt node 7 updated with: {combined_negative_prompt}")
        else:
            logger.warning("Node 7 (negative prompt) not found in workflow. Skipping negative prompt update.")
        
        # -------------------------------------------------------------
        # [수정 끝] 프롬프트 텍스트 및 카테고리 기반 프롬프트 조합 로직
        # -------------------------------------------------------------

        # 시드 업데이트 (23번 노드: 이 노드 ID는 ComfyUI 워크플로우에 따라 다를 수 있습니다.)
        # KSampler 또는 LatentFromNoise 노드의 seed를 업데이트한다고 가정
        seed_updated = False
        for node_id, node_data in prompt_workflow["nodes"].items():
            if "inputs" in node_data and "seed" in node_data["inputs"]:
                prompt_workflow["nodes"][node_id]["inputs"]["seed"] = seed
                logger.debug(f"Seed updated in node {node_id} to: {seed}")
                seed_updated = True
                break # 첫 번째 시드 노드만 업데이트한다고 가정
        if not seed_updated:
            logger.warning("No node with 'seed' input found. Seed might not be applied correctly.")


        # 모델 업데이트 (4번 노드: CheckpointLoaderSimple 노드 ID가 4라고 가정)
        if "4" in prompt_workflow["nodes"] and "ckpt_name" in prompt_workflow["nodes"]["4"]["inputs"]:
            prompt_workflow["nodes"]["4"]["inputs"]["ckpt_name"] = model_name
            logger.debug(f"Model updated to: {model_name}")
        else:
            logger.warning("Node 4 (model loader) not found or 'ckpt_name' input missing. Skipping model update.")

        # 이미지 크기 업데이트 (8번 노드: EmptyLatentImage 노드 ID가 8이라고 가정)
        if "8" in prompt_workflow["nodes"] and "width" in prompt_workflow["nodes"]["8"]["inputs"] and "height" in prompt_workflow["nodes"]["8"]["inputs"]:
            prompt_workflow["nodes"]["8"]["inputs"]["width"] = image_width
            prompt_workflow["nodes"]["8"]["inputs"]["height"] = image_height
            logger.debug(f"Image size updated to: {image_width}x{image_height}")
        else:
            logger.warning("Node 8 (latent image) not found or width/height inputs missing. Skipping size update.")

        # i2i 관련 노드 업데이트 (json_workflow_filename이 "img2img_api_workflow.json"일 경우)
        if workflow_json_filename == "img2img_api_workflow.json" and image_base64:
            # 24번 노드: Load Image (Base64) 노드라고 가정
            if "24" in prompt_workflow["nodes"] and "image_base64" in prompt_workflow["nodes"]["24"]["inputs"]:
                prompt_workflow["nodes"]["24"]["inputs"]["image_base64"] = image_base64
                logger.debug("Image base64 updated in node 24.")
            else:
                logger.warning("Node 24 (Load Image Base64) not found or 'image_base64' input missing. Skipping image base64 update.")

            # 23번 노드: KSampler (For I2I) 노드의 denoising_strength 업데이트라고 가정
            if "23" in prompt_workflow["nodes"] and "denoise" in prompt_workflow["nodes"]["23"]["inputs"]:
                prompt_workflow["nodes"]["23"]["inputs"]["denoise"] = denoising_strength
                logger.debug(f"Denoising strength updated to: {denoising_strength}")
            else:
                logger.warning("Node 23 (KSampler for i2i) not found or 'denoise' input missing. Skipping denoising strength update.")
        
        # LoRA 적용 (lora_model_name이 제공될 경우)
        if lora_model_name:
            # 22번 노드: LoRA Loader 노드 ID가 22라고 가정 (워크플로우에 따라 다를 수 있음)
            if "22" in prompt_workflow["nodes"] and \
               "lora_name" in prompt_workflow["nodes"]["22"]["inputs"] and \
               "strength_model" in prompt_workflow["nodes"]["22"]["inputs"] and \
               "strength_clip" in prompt_workflow["nodes"]["22"]["inputs"]:
                prompt_workflow["nodes"]["22"]["inputs"]["lora_name"] = lora_model_name
                prompt_workflow["nodes"]["22"]["inputs"]["strength_model"] = lora_strength_model
                prompt_workflow["nodes"]["22"]["inputs"]["strength_clip"] = lora_strength_clip
                logger.debug(f"LoRA '{lora_model_name}' applied with strengths model:{lora_strength_model}, clip:{lora_strength_clip}")
            else:
                logger.warning("Node 22 (LoRA Loader) not found or inputs missing. Skipping LoRA application.")

        # ComfyUI API 호출
        logger.info("Queuing prompt to ComfyUI...")
        response = await queue_prompt(prompt_workflow)
        
        prompt_id = response['prompt_id']
        logger.info(f"Prompt queued successfully with ID: {prompt_id}")

        # 이미지 생성 완료 대기 및 다운로드
        output_images = await get_images_from_history(prompt_id)
        
        if not output_images:
            logger.error(f"No images found for prompt ID: {prompt_id}")
            raise ValueError("No images generated by ComfyUI.")

        # 첫 번째 이미지 처리 (대부분 하나의 이미지를 생성한다고 가정)
        image_info = output_images[0]
        filename = image_info['filename']
        subfolder = image_info['subfolder']
        folder_type = image_info['type']

        # ComfyUI에서 이미지 다운로드
        image_content = await get_image(filename, subfolder, folder_type)
        
        # Django 스토리지에 이미지 저장
        # 이미지 파일명을 UUID로 변경하여 저장
        unique_filename = f"{uuid.uuid4()}.png" # PNG로 강제 저장
        
        # Django settings.COMFYUI_OUTPUT_DIR에 정의된 경로의 하위 폴더에 저장
        # 예를 들어, 'generated_images' 서브폴더에 저장한다고 가정 (settings.py에서 정의)
        subfolder_in_media = 'generated_images' 
        
        # 저장할 최종 경로 결정
        # Django storage 시스템에 맞는 경로를 생성
        django_storage_path = os.path.join(subfolder_in_media, unique_filename)

        # ContentFile를 사용하여 이미지 데이터를 저장 (Django storage 시스템 사용)
        saved_file_name = default_storage.save(django_storage_path, ContentFile(image_content))
        
        # 저장된 이미지의 완전한 파일 시스템 경로 (개발 환경에서만 유효)
        full_image_file_path = default_storage.path(saved_file_name)
        logger.info(f"Image saved to Django media: {full_image_file_path}")

        # 클라이언트에서 접근할 수 있는 URL (MEDIA_URL 기준)
        comfyui_served_image_url = default_storage.url(saved_file_name)


        return {
            'image_file_path': full_image_file_path, # 실제 파일 시스템 경로 (백엔드 내부용)
            'comfyui_image_url': comfyui_served_image_url # 클라이언트가 접근할 수 있는 URL
        }

    except FileNotFoundError as e:
        logger.error(f"JSON config file error: {e}", exc_info=True)
        raise
    except httpx.RequestError as e:
        logger.error(f"Error connecting to ComfyUI API or during image download: {e}", exc_info=True)
        raise
    except ValueError as e:
        logger.error(f"Value error in image generation logic: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.critical(f"An unexpected error occurred during image generation: {e}", exc_info=True)
        raise


async def get_images_from_history(prompt_id):
    """
    ComfyUI 히스토리에서 생성된 이미지 정보를 추출합니다.
    """
    while True:
        history = await get_history(prompt_id)
        if prompt_id in history:
            outputs = history[prompt_id]['outputs']
            images = []
            for node_id in outputs:
                for image in outputs[node_id].get('images', []):
                    images.append(image)
            if images:
                logger.info(f"Found {len(images)} images for prompt ID {prompt_id}.")
                return images
        logger.info(f"Waiting for image generation to complete for prompt ID: {prompt_id}...")
        await asyncio.sleep(1) # 1초 간격으로 재시도
