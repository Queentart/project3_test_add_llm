# D:\project3_test\llm_cores\translation_service.py

from transformers import pipeline
import os
import torch
import logging
from django.conf import settings # [추가 부분] settings 참조를 위해 임포트

logger = logging.getLogger(__name__)

# [추가 부분] 대상 언어 코드 정의
# 이 서비스는 현재 영어(en)로만 번역하도록 설계되어 있습니다.
TARGET_LANG_CODE = 'en'

# 각 언어 쌍별 번역 모델 인스턴스를 저장할 딕셔너리
_translators = {}

# 지원하는 원본 언어 및 해당 언어에서 영어로의 모델 이름 매핑
# 이 딕셔너리는 '원본언어' -> 'Helsinki-NLP/opus-mt-원본언어-en' 형태로 구성되어 있습니다.
LANGUAGE_MODELS = {
    "ko": "Helsinki-NLP/opus-mt-ko-en",
    "ja": "Helsinki-NLP/opus-mt-ja-en",
    "zh": "Helsinki-NLP/opus-mt-zh-en", # 중국어
    "fr": "Helsinki-NLP/opus-mt-fr-en", # 프랑스어
    "de": "Helsinki-NLP/opus-mt-de-en", # 독일어
    "es": "Helsinki-NLP/opus-mt-es-en", # 스페인어
    "it": "Helsinki-NLP/opus-mt-it-en", # 이탈리아어
    "ru": "Helsinki-NLP/opus-mt-ru-en", # 러시아어
    "ar": "Helsinki-NLP/opus-mt-ar-en", # 아랍어
    "th": "Helsinki-NLP/opus-mt-th-en", # 태국어
    "hi": "Helsinki-NLP/opus-mt-hi-en", # 힌디어
    "vi": "Helsinki-NLP/opus-mt-vi-en", # 베트남어
    "el": "Helsinki-NLP/opus-mt-el-en", # 그리스어
    "pt": "Helsinki-NLP/opus-mt-pt-en", # 포르투갈어
}

# [추가 부분] 번역기 인스턴스를 가져오는 함수
def get_translator_instance_for_lang(source_lang: str) -> pipeline:
    """
    주어진 원본 언어에 해당하는 번역기 파이프라인 인스턴스를 로드하거나 가져옵니다.
    이 함수는 항상 원본 언어에서 영어(en)로의 번역 모델을 로드합니다.
    """
    # 모델 키는 '원본언어-대상언어' 형태로, 대상 언어는 항상 TARGET_LANG_CODE(en)로 고정
    model_key = f"{source_lang}-{TARGET_LANG_CODE}"
    
    if model_key not in _translators:
        model_name = LANGUAGE_MODELS.get(source_lang)
        if not model_name:
            # 지원하지 않는 원본 언어인 경우 ValueError 발생
            raise ValueError(f"Unsupported source language: '{source_lang}'. No translation model found for this language.")
        
        # [주석 처리] cache_dir은 pipeline 생성 시 모델 캐싱 경로를 지정하는 용도이며,
        # model.generate() 메서드에 전달되는 인자가 아닙니다.
        # 이로 인해 "model_kwargs are not used by the model: ['cache_dir']" 오류가 발생했습니다.
        # Hugging Face는 기본 캐시 경로를 사용하므로, 명시적으로 지정하지 않아도 됩니다.
        # 만약 특정 캐시 경로가 필요하다면, 다른 방식으로 모델을 로드해야 할 수 있습니다.
        # cache_dir = os.path.join(base_dir, 'translation_models_cache')
        # os.makedirs(cache_dir, exist_ok=True)

        try:
            # device=0 if torch.cuda.is_available() else -1: GPU 사용 가능 시 GPU, 아니면 CPU
            # [수정 부분] cache_dir 인자 제거
            _translators[model_key] = pipeline(
                "translation", 
                model=model_name, 
                device=0 if torch.cuda.is_available() else -1
            )
            logger.info(f"Successfully loaded translation model: {model_name}")
        except Exception as e:
            logger.error(f"Error loading translation model {model_name}: {e}", exc_info=True)
            raise # 모델 로딩 실패 시 예외 다시 발생

    return _translators[model_key]

# [수정 부분] translate_text 함수
def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    주어진 텍스트를 원본 언어(source_lang)에서 대상 언어(target_lang)로 번역합니다.
    이 함수는 LANGUAGE_MODELS에 정의된 언어 쌍만 지원하며, 대상 언어는 항상 'en'입니다.
    """
    if not text:
        return ""

    # 대상 언어가 영어가 아니면 오류 반환
    if target_lang != TARGET_LANG_CODE:
        logger.warning(f"Unsupported target language code '{target_lang}'. This service can only translate TO English ('{TARGET_LANG_CODE}').")
        return f"Unsupported target language code '{target_lang}'. This service can only translate TO English ('{TARGET_LANG_CODE}')."

    try:
        # 요청된 언어에 대한 번역기 인스턴스 가져오기
        translator = get_translator_instance_for_lang(source_lang)
        
        # [주석 처리] get_translator_instance_for_lang에서 이미 예외를 발생시키므로 이 조건은 불필요할 수 있지만,
        # 만약 함수가 None을 반환하는 경우를 대비한 안전 코드이므로, 이대로 유지해도 무방합니다.
        # if translator is None: 
        #     logger.error("Translation service is unavailable for this language. Model failed to load.")
        #     return "Translation service is unavailable for this language. Model failed to load."

        # Hugging Face pipeline을 사용하여 번역 수행
        # [수정 부분] src_lang과 tgt_lang을 제거하고 텍스트만 전달
        translated_result = translator(text)
        
        # 번역 결과는 보통 리스트의 첫 번째 요소에 'translation_text' 키로 존재
        return translated_result[0]['translation_text']
    except ValueError as ve: 
        # get_translator_instance_for_lang에서 발생한 지원하지 않는 언어 오류 처리
        logger.error(f"Translation error: {ve}", exc_info=True)
        return str(ve) # 사용자에게 오류 메시지를 반환
    except Exception as e:
        # 번역 과정 중 발생할 수 있는 다른 예외 처리
        logger.error(f"Error during translation process for '{source_lang}'->'{target_lang}': {e}", exc_info=True)
        return f"Translation failed due to an internal error: {e}"

# [주석 처리] requests 및 json 모듈은 이 스크립트에서 직접 사용되지 않으므로 주석 처리하거나 제거할 수 있습니다.
# import requests
# import json

# [주석 처리] 병렬 다운로드를 위한 import는 사용되지 않으므로 주석 처리합니다.
# from concurrent.futures import ThreadPoolExecutor, as_completed

# 테스트 코드 (이 부분은 파일의 가장 아래에 위치해야 합니다)
if __name__ == "__main__":
    # GPU 사용 가능 여부 확인
    if torch.cuda.is_available():
        print("CUDA is available! Using GPU for translation.")
    else:
        print("CUDA is not available. Using CPU for translation.")

    test_prompts = {
        "ko": "안녕하세요, 세계! 오늘 날씨가 정말 좋네요.", # 한국어: 안녕, 세상! 오늘 날씨 정말 좋네요.
        "ja": "こんにちは、世界！お元気ですか？", # 일본어: 안녕하세요, 잘 지내세요?
        "zh": "你好，世界，今天天气真好！", # 중국어: 안녕, 세상, 오늘 날씨 정말 좋다!
        "fr": "La vie est belle.", # 프랑스어: 인생은 아름다워.
        "de": "Ich liebe Programmierung.", # 독일어: 저는 프로그래밍을 사랑합니다.
        "es": "Me gusta aprender idiomas.", # 스페인어: 저는 언어를 배우는 것을 좋아합니다.
        "it": "Ciao, come stai?", # 이탈리아어: 안녕, 어떻게 지내?
        "ru": "Привет, как дела?", # 러시아어: 안녕, 어떻게 지내?
        "ar": "مرحبا يا عالم", # 아랍어: 안녕하세요 세상
        "th": "สวัสดีครับ", # 태국어: 안녕하세요 (남성형)
        "hi": "नमस्ते दुनिया", # 힌디어: 안녕하세요 세상
        "vi": "Xin chào thế giới", # 베트남어: 안녕하세요 세상
        "el": "Γεια σου κόσ메!", # 그리스어: 안녕, 세상!
        "pt": "Olá, mundo!", # 포르투갈어: 안녕, 세상!
    }

    # 각 언어에 대해 번역 테스트 실행
    for lang_code, text in test_prompts.items():
        print(f"Original ({lang_code.upper()}): {text}")
        # [수정] source_lang과 target_lang을 명시적으로 전달
        print(f"Translated (EN): {translate_text(text, source_lang=lang_code, target_lang='en')}")
        print("-" * 30)
