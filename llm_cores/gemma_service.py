import requests
import json
from django.conf import settings # settings.py에 Ollama URL을 넣고 싶다면 필요합니다.

# --- Ollama API 설정 ---
# 이 URL을 여기에 직접 넣을 수도 있고, Django settings.py에 추가할 수도 있습니다.
# settings.py에 추가한다면, 반드시 정의해 주세요 (예: OLLAMA_API_URL = "http://localhost:11434/api/generate")
OLLAMA_API_URL = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL_NAME = getattr(settings, 'OLLAMA_MODEL_NAME', 'gemma3:latest') # Ollama로 'gemma'를 pull했다고 가정합니다.

def get_docent_response(prompt: str) -> str:
    """
    로컬 Ollama Gemma 모델로부터 응답을 생성합니다.
    """
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False # 스트리밍 응답을 원한다면 True로 설정하세요.
    }

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