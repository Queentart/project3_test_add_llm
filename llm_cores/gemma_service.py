import requests
import json
from django.conf import settings # settings.py에 Ollama URL을 넣고 싶다면 필요합니다.

# --- Ollama API 설정 ---
# 이 URL을 여기에 직접 넣을 수도 있고, Django settings.py에 추가할 수도 있습니다.
# settings.py에 추가한다면, 반드시 정의해 주세요 (예: OLLAMA_API_URL = "http://localhost:11434/api/generate")
OLLAMA_API_URL = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL_NAME = getattr(settings, 'OLLAMA_MODEL_NAME', 'gemma3:latest') # Ollama로 'gemma'를 pull했다고 가정합니다.

# [수정 사항] image_data_base64 파라미터 추가
def get_docent_response(prompt: str, image_data_base64: str = None) -> str:
    """
    로컬 Ollama Gemma 모델로부터 응답을 생성합니다.
    GPU 활용 및 GPU RAM이 부족할 경우 CPU로 오프로드하는 로직을 포함하며,
    이미지 데이터(Base64)를 받아 멀티모달 추론을 수행할 수 있습니다.
    """
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False, # 스트리밍 응답을 원한다면 True로 설정하세요.
        # "stream": True, # 스트리밍 응답을 원한다면 True로 설정하세요.
        "options": {
            # num_gpu: GPU에 로드할 레이어 수를 지정합니다.
            # 99 (또는 매우 큰 숫자)로 설정하면 Ollama가 가능한 한 많은 레이어를 GPU에 로드하려고 시도하고,
            # GPU RAM이 부족하면 자동으로 나머지 레이어를 CPU로 오프로드합니다.
            # 특정 숫자로 설정하면 해당 레이어만 GPU에 로드됩니다.
            "num_gpu": 99
        }
    }

    # [추가 사항] 이미지 데이터가 있을 경우 payload에 'images' 필드 추가
    if image_data_base64:
        payload["images"] = [image_data_base64]
        # 이미지 분석을 위한 프롬프트 조정 (선택 사항)
        # 사용자가 텍스트 프롬프트를 제공하지 않고 이미지만 올렸을 경우 기본 프롬프트 설정
        if not prompt.strip():
            payload["prompt"] = "이 이미지에 대해 설명해 주세요." # 기본 이미지 분석 프롬프트

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status() # HTTP 오류(4xx 또는 5xx) 발생 시 예외를 발생시킵니다.

        response_data = response.json()
        # Ollama의 /api/generate 엔드포인트는 'response' 필드에 응답을 반환합니다.
        return response_data.get('response', '').strip()

    except requests.exceptions.ConnectionError:
        print(f"오류: {OLLAMA_API_URL}의 Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인가요?")
        return "죄송합니다. 도슨트 기능을 사용할 수 없습니다. 로컬 AI 서버에 연결할 수 없습니다."
    except requests.exceptions.RequestException as e:
        print(f"Ollama 모델 호출 중 오류 발생: {e}")
        return f"죄송합니다. 도슨트 기능을 사용하는 중 오류가 발생했습니다: {e}"
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")
        return "죄송합니다. 알 수 없는 오류가 발생했습니다."

