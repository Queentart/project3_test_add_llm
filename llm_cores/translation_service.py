# D:\project3_test\llm_cores\translation_service.py

from transformers import pipeline
import os
import torch
# from concurrent.futures import ThreadPoolExecutor, as_completed # 병렬 다운로드를 위해 추가 (이제 사용 안 함)

# 각 언어 쌍별 번역 모델 인스턴스를 저장할 딕셔너리
_translators = {}

# 지원하는 원본 언어 및 해당 언어에서 영어로의 모델 이름 매핑
# 여기에 필요한 모든 언어를 추가하세요.
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
    "pt": "Helsinki-NLP/opus-mt-ROMANCE-en", # 포르투갈어 (로망스어 통합 모델)
    "el": "Helsinki-NLP/opus-mt-tc-big-el-en", # 그리스어
    # 더 많은 언어가 필요하면 여기에 추가: "언어코드": "Helsinki-NLP/opus-mt-언어코드-en"
}
TARGET_LANG_CODE = "en" # 이 프로젝트의 대상 언어는 항상 영어입니다.

# CPU/GPU 장치 설정 (전역으로 한 번만 결정)
# 기본적으로 CPU를 사용하도록 강제 설정합니다. GPU 문제를 우회하기 위함입니다.
_device = -1 # <--- CPU 사용을 강제!
_device_name = 'cpu' # <--- 장치 이름도 'cpu'로 설정

# 만약 GPU를 사용하고 싶고, 위의 문제가 해결되었다면 아래 코드로 변경:
# _device = 0 if torch.cuda.is_available() else -1
# _device_name = 'cuda:0' if _device == 0 else 'cpu'


def get_translator_instance_for_lang(source_lang: str):
    """
    특정 원본 언어(source_lang)에서 영어로 번역하는 모델 인스턴스를 반환합니다.
    모델은 첫 호출 시 다운로드 및 로드되며, GPU가 사용 가능한 경우 GPU를 활용합니다.
    """
    if source_lang not in LANGUAGE_MODELS:
        # 지원하지 않는 언어 요청 시 ValueError 발생
        raise ValueError(f"Unsupported source language: '{source_lang}'. Supported languages are: {list(LANGUAGE_MODELS.keys())}")

    # 이미 로드되었거나 로드 시도 중인 모델인 경우 캐시된 인스턴스 반환
    # None은 로딩 실패를 의미
    if source_lang not in _translators or _translators[source_lang] is None:
        model_name = LANGUAGE_MODELS[source_lang]
        try:
            print(f"Loading translation model '{model_name}' on device: {_device_name}")

            _translators[source_lang] = pipeline(
                "translation",
                model=model_name,
                device=_device
            )
            print(f"Translation model '{model_name}' loaded successfully.")
        except Exception as e:
            print(f"Error loading translation model '{model_name}': {e}")
            print("Initial download requires internet. Check connectivity or disk space. If issue persists, consider updating PyTorch/Transformers or trying on CPU.")
            _translators[source_lang] = None # 로딩 실패 시 None으로 유지하여 오류를 알림
    return _translators[source_lang]

def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    """
    주어진 텍스트를 원본 언어(source_lang)에서 대상 언어(target_lang)로 번역합니다.
    이 함수는 LANGUAGE_MODELS에 정의된 언어 쌍만 지원하며, 대상 언어는 항상 'en'입니다.
    """
    # 대상 언어가 영어가 아니면 오류 반환
    if target_lang != TARGET_LANG_CODE:
        return f"Unsupported target language code '{target_lang}'. This service can only translate TO English ('{TARGET_LANG_CODE}')."

    try:
        # 요청된 언어에 대한 번역기 인스턴스 가져오기
        translator = get_translator_instance_for_lang(source_lang)
        if translator is None:
            # 모델 로딩에 실패하여 번역기 인스턴스가 None인 경우
            return "Translation service is unavailable for this language. Model failed to load."

        # Hugging Face pipeline을 사용하여 번역 수행
        # src_lang과 tgt_lang을 명시적으로 전달하여 정확한 언어 쌍 사용
        translated_result = translator(text, src_lang=source_lang, tgt_lang=target_lang)
        
        # 번역 결과는 보통 리스트의 첫 번째 요소에 'translation_text' 키로 존재
        return translated_result[0]['translation_text']
    except ValueError as ve: 
        # get_translator_instance_for_lang에서 발생한 지원하지 않는 언어 오류 처리
        print(f"Translation error: {ve}")
        return str(ve) # 사용자에게 오류 메시지를 반환
    except Exception as e:
        # 번역 과정 중 발생할 수 있는 다른 예외 처리
        print(f"Error during translation process for '{source_lang}'->'{target_lang}': {e}")
        return f"Translation failed due to an internal error: {e}"

def download_all_models():
    """
    LANGUAGE_MODELS에 정의된 모든 번역 모델을 미리 다운로드합니다.
    (순차적으로 다운로드하여 안정성을 높임)
    """
    print(f"Attempting to download all {len(LANGUAGE_MODELS)} translation models sequentially...")
    
    for lang_code in LANGUAGE_MODELS.keys():
        try:
            get_translator_instance_for_lang(lang_code)
            print(f"Successfully downloaded/loaded model: {LANGUAGE_MODELS[lang_code]}")
        except Exception as e:
            print(f"Failed to download/load model {LANGUAGE_MODELS[lang_code]} for language '{lang_code}': {e}")
                
    print("All model download attempts completed.")

# 이 파일을 직접 실행하여 테스트할 때만 동작하는 코드
if __name__ == "__main__":
    print("--- Testing translation_service.py ---")
    
    # 모든 모델 다운로드 및 로드 시도
    # 이 과정은 네트워크 상태 및 시스템 성능에 따라 시간이 오래 걸릴 수 있습니다.
    download_all_models()
    print("\n--- Running Translation Tests ---")

    # 각 언어별 테스트 프롬프트
    test_prompts = {
        "ko": "고요한 호수 위에 떠 있는 달",
        "ja": "こんにちは、元気ですか？", # 일본어: 안녕하세요, 잘 지내세요?
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
        "el": "Γεια σου κόσμε!", # 그리스어: 안녕, 세상!
        "pt": "Olá, mundo!", # 포르투갈어: 안녕, 세상!
    }

    # 각 언어에 대해 번역 테스트 실행
    for lang_code, text in test_prompts.items():
        print(f"Original ({lang_code.upper()}): {text}")
        print(f"Translated (EN): {translate_text(text, lang_code, 'en')}")
        print("-" * 30)

    # 잘못된 대상 언어 테스트 (이 모델들은 영어로만 번역 가능)
    test_text_invalid_target = "Hello World"
    print(f"Original (KO): {test_text_invalid_target}")
    print(f"Translated (KO - Invalid Target): {translate_text(test_text_invalid_target, 'ko', 'ko')}")
    print("-" * 30)

    # 지원하지 않는 원본 언어 테스트
    test_text_unsupported_source = "Habari dunia" # Swahili for "Hello world"
    print(f"Original (SW): {test_text_unsupported_source}")
    print(f"Translated (EN - Unsupported Source): {translate_text(test_text_unsupported_source, 'sw', 'en')}")
    print("-" * 30)