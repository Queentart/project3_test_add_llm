# vietnamese_to_english_model_downloader.py

import os
from transformers import pipeline
import torch

# --- (필수) 캐시 경로 강제 지정 ---
# Hugging Face 모델이 저장될 최상위 캐시 디렉토리를 지정합니다.
# 실제 모델은 이 경로 아래에 'hub' 폴더 내에 저장됩니다.
# 예: C:\Users\freedom\.cache\huggingface\hub\models--Helsinki-NLP--opus-mt-vi-en 여기에 저장됩니다.
os.environ["HF_HOME"] = r"C:\Users\freedom\.cache\huggingface"
# -----------------------------------

def download_vietnamese_to_english_model():
    """
    Helsinki-NLP/opus-mt-vi-en 번역 모델을 다운로드하고 로드합니다.
    """
    model_name = "Helsinki-NLP/opus-mt-vi-en" # 베트남어 모델 지정

    # CPU/GPU 장치 설정
    # -1은 CPU를 의미합니다. GPU를 사용하고 싶다면 0으로 변경하세요.
    device = -1 # 강제로 CPU 사용
    device_name = 'cpu'

    print(f"'{model_name}' 모델을 '{device_name}' 장치에 다운로드 및 로드 시도...")
    print(f"예상 캐시 폴더: '{os.getenv('HF_HOME', os.path.join(os.path.expanduser('~'), '.cache', 'huggingface'))}\\hub\\models--{model_name.replace('/', '--')}' 입니다.")

    try:
        # pipeline 함수가 모델을 자동으로 다운로드하고 로드합니다.
        # 첫 다운로드 시에는 시간이 걸릴 수 있습니다.
        translator = pipeline("translation", model=model_name, device=device)
        print(f"'{model_name}' 모델이 성공적으로 다운로드 및 로드되었습니다.")

        # 모델 로드 확인을 위한 간단한 번역 테스트
        test_text = "Xin chào thế giới" # 베트남어: 안녕하세요 세상
        translated_result = translator(test_text, src_lang="vi", tgt_lang="en")
        print(f"\n테스트 번역:")
        print(f"원본 (VI): {test_text}")
        print(f"번역 (EN): {translated_result[0]['translation_text']}")

    except Exception as e:
        print(f"오류: '{model_name}' 모델을 다운로드하거나 로드하는 데 실패했습니다.")
        print(f"자세한 오류: {e}")
        print("네트워크 연결을 확인하거나, 디스크 공간이 충분한지 확인하세요.")
        print("만약 CPU 사용 중에도 오류가 발생한다면, PyTorch나 Transformers 라이브러리 업데이트를 고려해보세요.")

if __name__ == "__main__":
    download_vietnamese_to_english_model()