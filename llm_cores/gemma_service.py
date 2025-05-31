import requests
import json
import logging # logging 모듈 임포트 추가
from django.conf import settings # settings.py에 Ollama URL을 넣고 싶다면 필요합니다.

logger = logging.getLogger(__name__) # 로거 인스턴스 생성

# --- Ollama API 설정 ---
# 이 URL을 여기에 직접 넣을 수도 있고, Django settings.py에 추가할 수도 있습니다.
# settings.py에 추가한다면, 반드시 정의해 주세요 (예: OLLAMA_API_URL = "http://localhost:11434/api/generate")
OLLAMA_API_URL = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL_NAME = getattr(settings, 'OLLAMA_MODEL_NAME', 'gemma3:latest') # Ollama로 'gemma'를 pull했다고 가정합니다.

# [수정 사항] image_data_base64 파라미터 추가 (기존 유지)
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
        # [수정] 'options' 필드는 /api/generate 엔드포인트에서 400 Bad Request의 원인이 될 수 있으므로 제거합니다.
        # Ollama의 'num_gpu' 설정은 'ollama run' 명령이나 모델 파일 자체에서 이루어지는 경우가 많습니다.
        # "options": {
        #     "num_gpu": 99
        # }
    }

    # [추가 사항] 이미지 데이터가 있을 경우 payload에 'images' 필드 추가 (기존 유지)
    if image_data_base64:
        payload["images"] = [image_data_base64]
        # 이미지 분석을 위한 프롬프트 조정 (선택 사항)
        # 사용자가 텍스트 프롬프트를 제공하지 않고 이미지만 올렸을 경우 기본 프롬프트 설정
        if not prompt.strip():
            payload["prompt"] = "이 이미지에 대해 설명해 주세요." # 기본 이미지 분석 프롬프트

    logger.info(f"Sending request to Ollama API: {json.dumps(payload, ensure_ascii=False)}") # 로깅 추가

    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status() # HTTP 오류(4xx 또는 5xx) 발생 시 예외를 발생시킵니다.

        response_data = response.json()
        # Ollama의 /api/generate 엔드포인트는 'response' 필드에 응답을 반환합니다.
        docent_response = response_data.get('response', '').strip()
        logger.info(f"Received response from Ollama API: {docent_response[:100]}...") # 로깅 추가
        return docent_response

    except requests.exceptions.ConnectionError as e: # 예외 변수 추가
        logger.error(f"오류: {OLLAMA_API_URL}의 Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인가요? 오류: {e}", exc_info=True) # 로깅으로 변경
        return "죄송합니다. 도슨트 기능을 사용할 수 없습니다. 로컬 AI 서버에 연결할 수 없습니다."
    except requests.exceptions.RequestException as e: # 예외 변수 추가
        logger.error(f"Ollama 모델 호출 중 요청 오류 발생: {e}. 응답: {response.text if 'response' in locals() else 'N/A'}", exc_info=True) # 로깅으로 변경, 응답 텍스트 추가
        return f"죄송합니다. 도슨트 기능을 사용하는 중 오류가 발생했습니다: {e}"
    except json.JSONDecodeError as e: # JSON 디코딩 오류 추가
        logger.error(f"Ollama API 응답 JSON 디코딩 오류: {e}. 응답 텍스트: {response.text if 'response' in locals() else 'N/A'}", exc_info=True)
        return f"죄송합니다. 도슨트 서비스 응답을 처리하는 중 오류가 발생했습니다: {e}"
    except Exception as e: # 일반 예외 처리
        logger.error(f"도슨트 서비스에서 예상치 못한 오류 발생: {e}", exc_info=True) # 로깅으로 변경
        return "죄송합니다. 알 수 없는 오류가 발생했습니다."

