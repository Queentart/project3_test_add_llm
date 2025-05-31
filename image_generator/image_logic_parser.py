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
# [수정] Ollama 번역 함수 대신 기존 translation_service의 translate_text 함수 임포트
from llm_cores.translation_service import translate_text 

logger = logging.getLogger(__name__)

# JSON 파일들이 위치한 디렉토리 경로 (프로젝트 루트 기준으로 설정)
BASE_DIR = settings.BASE_DIR
JSON_DEFINITIONS_DIR = os.path.join(BASE_DIR, 'comfyui_workflows')

# ComfyUI API 호출 설정 (settings에서 직접 가져옴)
COMFYUI_API_URL = settings.COMFYUI_API_URL
COMFYUI_HISTORY_URL = settings.COMFYUI_HISTORY_URL
COMFYUI_IMAGE_URL = settings.COMFYUI_IMAGE_URL
COMFYUI_INPUT_DIR = getattr(settings, 'COMFYUI_INPUT_DIR', os.path.join(BASE_DIR, 'comfyui_input'))


# [수정] generate_image_based_on_json_logic 함수의 매개변수 이름을 'uploaded_image_path'로 명확히 일치시켰습니다.
async def generate_image_based_on_json_logic(user_input, uploaded_image_path, mode, positive_categories, negative_categories):
    """
    주어진 사용자 입력, 이미지 파일 경로, 모드 및 프롬프트 카테고리에 따라 ComfyUI를 사용하여 이미지를 생성합니다.

    Args:
        user_input (str): 사용자가 입력한 텍스트 프롬프트.
        uploaded_image_path (str or None): 업로드된 이미지 파일의 실제 파일 시스템 경로 (image-to-image 모드용).
        mode (str): 'image_generation' 또는 'curator'.
        positive_categories (list): 적용할 긍정 프롬프트 카테고리 목록.
        negative_categories (list): 적용할 부정 프롬프트 카테고리 목록.

    Returns:
        dict: 생성된 이미지의 파일 경로 및 ComfyUI URL을 포함하는 딕셔너리.
    """
    try:
        # 1. 워크플로우 JSON 파일 로드
        # [수정] image_file 대신 uploaded_image_path의 존재 여부로 모드 판단
        json_file_name = 'image_to_image.json' if uploaded_image_path else 'text_to_image.json'
        json_path = os.path.join(JSON_DEFINITIONS_DIR, json_file_name)

        if not os.path.exists(json_path):
            logger.error(f"JSON config file not found: {json_path}")
            raise FileNotFoundError(f"JSON config file not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            prompt_workflow = json.load(f)

        # ComfyUI API는 'prompt' 키 아래에 실제 워크플로우 그래프를 기대합니다.
        # JSON 파일 자체가 워크플로우인 경우도 있으므로, 'prompt' 키가 없으면 전체를 사용합니다.
        json_data = prompt_workflow.get('prompt', prompt_workflow)

        # 2. 프롬프트 업데이트 (긍정/부정)
        # 사용자 입력(user_input)을 기존 translation_service를 사용하여 영어로 번역
        translated_user_input = translate_text(user_input, source_lang='ko', target_lang='en')
        if not translated_user_input or "Translation failed" in translated_user_input: # 번역 실패 시 원본 사용 또는 오류 처리
            logger.warning(f"Translation failed for '{user_input}', using original text.")
            translated_user_input = user_input # 번역 실패 시 원본 텍스트 사용

        # 긍정 프롬프트 조합: 번역된 사용자 입력 + 선택된 긍정 카테고리 프롬프트
        combined_positive_prompt_parts = [translated_user_input]
        for category in positive_categories:
            if category in POSITIVE_PROMPT_MAP:
                combined_positive_prompt_parts.append(POSITIVE_PROMPT_MAP[category])
        combined_positive_prompt_text = ", ".join(filter(None, combined_positive_prompt_parts))

        # 부정 프롬프트 조합: 기본 부정 프롬프트 + 선택된 부정 카테고리 프롬프트
        combined_negative_prompt_parts = []
        
        # 기본 부정 프롬프트는 항상 추가
        default_negative_prompt = NEGATIVE_PROMPT_MAP.get("bad_quality", "low quality, bad quality")
        if default_negative_prompt:
            combined_negative_prompt_parts.append(default_negative_prompt)

        # 사용자가 선택한 카테고리별 부정 프롬프트를 추가 (중복 방지)
        for category in negative_categories:
            if category in NEGATIVE_PROMPT_MAP:
                prompt_from_category = NEGATIVE_PROMPT_MAP[category]
                if prompt_from_category and prompt_from_category not in combined_negative_prompt_parts:
                    combined_negative_prompt_parts.append(prompt_from_category)
        
        combined_negative_prompt_text = ", ".join(filter(None, combined_negative_prompt_parts))

        # 워크플로우 JSON에서 긍정/부정 프롬프트 노드 찾기 및 업데이트
        if json_file_name == 'text_to_image.json':
            # text_to_image.json의 경우 "6"과 "7" 노드가 CLIPTextEncode에 해당
            if '6' in json_data and 'inputs' in json_data['6'] and 'text' in json_data['6']['inputs']:
                json_data['6']['inputs']['text'] = combined_positive_prompt_text
                logger.info(f"Updated positive prompt in node 6: {combined_positive_prompt_text}")
            else:
                logger.warning("Node '6' or its 'inputs.text' not found for positive prompt in text_to_image workflow.")

            if '7' in json_data and 'inputs' in json_data['7'] and 'text' in json_data['7']['inputs']:
                json_data['7']['inputs']['text'] = combined_negative_prompt_text
                logger.info(f"Updated negative prompt in node 7: {combined_negative_prompt_text}")
            else:
                logger.warning("Node '7' or its 'inputs.text' not found for negative prompt in text_to_image workflow.")
        
        elif json_file_name == 'image_to_image.json':
            # image_to_image.json의 경우 "11"과 "10" 노드가 CLIPTextEncodeLumina2에 해당
            if '11' in json_data and 'inputs' in json_data['11'] and 'user_prompt' in json_data['11']['inputs']:
                json_data['11']['inputs']['user_prompt'] = combined_positive_prompt_text
                logger.info(f"Updated positive user_prompt in node 11 (Lumina2): {combined_positive_prompt_text}")
            else:
                logger.warning("Node '11' or its 'inputs.user_prompt' not found for Lumina2 positive prompt in image_to_image workflow.")

            if '10' in json_data and 'inputs' in json_data['10'] and 'user_prompt' in json_data['10']['inputs']:
                json_data['10']['inputs']['user_prompt'] = combined_negative_prompt_text
                logger.info(f"Updated negative user_prompt in node 10 (Lumina2): {combined_negative_prompt_text}")
            else:
                logger.warning("Node '10' or its 'inputs.user_prompt' not found for Lumina2 negative prompt in image_to_image workflow.")


        # 3. KSampler (Seed, Denoise, CFG) 가중치 업데이트
        ksampler_node_id = None
        if json_file_name == 'text_to_image.json':
            ksampler_node_id = '3' # text_to_image.json의 KSampler 노드 ID
        elif json_file_name == 'image_to_image.json':
            ksampler_node_id = '5' # image_to_image.json의 KSampler 노드 ID

        if ksampler_node_id and ksampler_node_id in json_data and \
           'inputs' in json_data[ksampler_node_id]:
            # 시드 값 랜덤 설정
            if 'seed' in json_data[ksampler_node_id]['inputs']:
                json_data[ksampler_node_id]['inputs']['seed'] = random.randint(0, 2**32 - 1)
                logger.info(f"Updated KSampler seed in node {ksampler_node_id}: {json_data[ksampler_node_id]['inputs']['seed']}")

            # Denoise 값 조절 (특히 image-to-image 모드에서)
            if 'denoise' in json_data[ksampler_node_id]['inputs']:
                if uploaded_image_path: # Image-to-Image 모드일 때
                    # 원본 이미지의 형태를 보존하면서 스타일을 적용하기 위한 값 (0.5 ~ 0.8)
                    json_data[ksampler_node_id]['inputs']['denoise'] = 0.7 
                    logger.info(f"Updated KSampler denoise for image-to-image in node {ksampler_node_id}: {json_data[ksampler_node_id]['inputs']['denoise']}")
                else: # Text-to-Image 모드일 때
                    # Text-to-Image에서는 완전히 무작위 노이즈에서 시작하므로 1.0이 기본값입니다.
                    json_data[ksampler_node_id]['inputs']['denoise'] = 1.0 
                    logger.info(f"Set KSampler denoise for text-to-image in node {ksampler_node_id}: {json_data[ksampler_node_id]['inputs']['denoise']}")
            else:
                logger.warning(f"Node '{ksampler_node_id}' has no 'denoise' input.")
            
            # CFG (Classifier Free Guidance) 값 조절
            if 'cfg' in json_data[ksampler_node_id]['inputs']:
                # 프롬프트의 영향력을 조절합니다. 스타일 적용을 강화하기 위해 8.0에서 9.0으로 상향 조정.
                # 일반적으로 7.0 ~ 10.0 사이에서 최적값을 찾습니다.
                json_data[ksampler_node_id]['inputs']['cfg'] = 9.0 # 제안값: 9.0
                logger.info(f"Updated KSampler cfg in node {ksampler_node_id}: {json_data[ksampler_node_id]['inputs']['cfg']}")
            else:
                logger.warning(f"Node '{ksampler_node_id}' has no 'cfg' input.")

        else:
            logger.warning(f"Node '{ksampler_node_id}' or its 'inputs' not found for KSampler in workflow {json_file_name}.")

        # 4. IPAdapter Weight 업데이트 (Image-to-Image 전용)
        if uploaded_image_path and json_file_name == 'image_to_image.json':
            ipadapter_node_id = '7' # IPAdapter Advanced 노드 ID
            if ipadapter_node_id in json_data and \
               'inputs' in json_data[ipadapter_node_id] and 'weight' in json_data[ipadapter_node_id]['inputs']:
                # IPAdapter의 weight 조절.
                # 이 값이 높을수록 원본 이미지의 스타일이나 내용이 더 강하게 반영됩니다.
                # 'denoise'와 함께 조절하여 원본 형태 보존과 새로운 화풍 적용의 조화를 찾습니다.
                # 현재는 1.0으로 유지하여 원본 이미지의 내용 반영을 돕고, 화풍은 CFG와 프롬프트에 더 의존합니다.
                json_data[ipadapter_node_id]['inputs']['weight'] = 1.0 # 제안값: 1.0
                logger.info(f"Updated IPAdapter weight in node {ipadapter_node_id}: {json_data[ipadapter_node_id]['inputs']['weight']}")
            else:
                logger.warning(f"Node '{ipadapter_node_id}' or its 'inputs.weight' not found for IPAdapter.")


        # 5. image-to-image 특정 로직 처리 (LoadImage 노드 업데이트)
        if uploaded_image_path:
            # 업로드된 이미지 파일을 ComfyUI input 디렉토리에 저장
            # Django storage를 통해 이미 저장된 파일이므로, 해당 경로에서 읽어와 ComfyUI input에 복사합니다.
            # 파일명을 UUID로 생성하여 중복 방지
            file_extension = os.path.splitext(uploaded_image_path)[1] # 경로에서 확장자 추출
            input_filename = f"{uuid.uuid4()}{file_extension}"
            comfyui_target_path = os.path.join(settings.COMFYUI_INPUT_DIR, input_filename)

            # [수정] default_storage.open을 사용하여 이미 저장된 파일을 읽습니다.
            with default_storage.open(uploaded_image_path, 'rb') as f:
                image_content = f.read()
                # ComfyUI input 디렉토리에 ContentFile로 저장
                saved_input_file_name = default_storage.save(comfyui_target_path, ContentFile(image_content))
            
            full_input_file_path = default_storage.path(saved_input_file_name)
            logger.info(f"Uploaded image copied to ComfyUI input: {full_input_file_path}")

            # ComfyUI 워크플로우의 LoadImage 노드 업데이트 (일반적으로 "9"번 노드)
            if '9' in json_data and 'inputs' in json_data['9'] and 'image' in json_data['9']['inputs']:
                json_data['9']['inputs']['image'] = input_filename
                logger.info(f"Updated LoadImage node 9 with filename: {input_filename}")
            else:
                logger.warning("Node '9' or its 'inputs.image' not found for LoadImage in workflow.")


        # 6. ComfyUI API 호출 및 이미지 생성 완료 대기, 다운로드
        logger.info(f"Final JSON data to send to ComfyUI: {json.dumps(json_data, indent=2)}")

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(f"{COMFYUI_API_URL}/prompt", json={'prompt': json_data})
            response.raise_for_status() # HTTP 오류가 발생하면 예외를 발생시킵니다.

            prompt_id = response.json()['prompt_id']
            logger.info(f"ComfyUI prompt submitted, ID: {prompt_id}")

            # 이미지 생성 완료 대기 및 다운로드
            while True:
                history_response = await client.get(f"{COMFYUI_HISTORY_URL}?prompt_id={prompt_id}")
                history_response.raise_for_status()
                history_data = history_response.json()

                if 'history' in history_data and str(prompt_id) in history_data['history']:
                    outputs = history_data['history'][str(prompt_id)]['outputs']
                elif str(prompt_id) in history_data:
                    outputs = history_data[str(prompt_id)]['outputs']
                else:
                    await asyncio.sleep(1)
                    continue

                image_info = None
                for node_id in outputs:
                    if 'images' in outputs[node_id]:
                        image_info = outputs[node_id]['images'][0] # 첫 번째 이미지를 가져옵니다.
                        break
                if image_info:
                    filename = image_info['filename']
                    subfolder = image_info['subfolder']
                    type = image_info['type']
                    break
                await asyncio.sleep(1) # 1초 대기 후 다시 폴링

            comfyui_served_image_url = f"{COMFYUI_IMAGE_URL}?filename={filename}&subfolder={subfolder}&type={type}"
            logger.info(f"Generated image URL from ComfyUI: {comfyui_served_image_url}")

            # 7. 생성된 이미지 다운로드 및 Django 스토리지에 저장
            image_response = await client.get(comfyui_served_image_url, timeout=300)
            image_response.raise_for_status()
        
        if subfolder:
            django_storage_path = os.path.join(settings.COMFYUI_OUTPUT_DIR, subfolder, filename)
        else:
            django_storage_path = os.path.join(settings.COMFYUI_OUTPUT_DIR, filename)

        saved_file_name = default_storage.save(django_storage_path, ContentFile(image_response.content))
        
        full_image_file_path = default_storage.path(saved_file_name)
        logger.info(f"Image saved to Django media: {full_image_file_path}")

        return {
            'image_file_path': full_image_file_path,
            'comfyui_image_url': comfyui_served_image_url
        }

    except FileNotFoundError as e:
        logger.error(f"JSON config file error: {e}", exc_info=True)
        raise
    except httpx.RequestError as e:
        logger.error(f"Error connecting to ComfyUI API or during image download: {e}", exc_info=True)
        if "client has been closed" in str(e).lower():
            logger.error("HTTPX client closed error. Ensure AsyncClient is properly used within 'async with' context or manually closed.")
        raise
    except ValueError as e:
        logger.error(f"Value error in image generation logic: {e}", exc_info=True)
        raise
    except json.JSONDecodeError as e:
        logger.error(f"JSON decoding error in workflow file: {e}", exc_info=True)
        raise
    except KeyError as e:
        logger.error(f"Missing key in ComfyUI workflow JSON: {e}. Please check your workflow JSON files.", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during image generation: {e}", exc_info=True)
        raise
