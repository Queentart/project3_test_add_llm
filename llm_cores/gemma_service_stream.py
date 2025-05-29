# llm_cores/gemma_service_streaming.py

import requests
import json
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# --- Ollama API 설정 ---
OLLAMA_API_URL = getattr(settings, 'OLLAMA_API_URL', 'http://localhost:11434/api/generate')
OLLAMA_MODEL_NAME = getattr(settings, 'OLLAMA_MODEL_NAME', 'gemma3:latest')

def get_docent_response_streaming(prompt: str, image_data_base64: str = None) -> str:
    """
    로컬 Ollama Gemma 모델로부터 스트리밍 응답을 생성합니다.
    응답을 청크 단위로 받아 처리하고 최종 텍스트를 반환합니다.
    """
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": True, # <--- 스트리밍을 True로 설정
        "options": {
            "num_gpu": 99
        }
    }

    if image_data_base64:
        payload["images"] = [image_data_base64]
        if not prompt.strip():
            payload["prompt"] = "이 이미지에 대해 설명해 주세요."

    full_ai_response_chunks = [] # 스트리밍으로 받은 응답 청크들을 저장할 리스트

    try:
        # requests.post 호출 시 stream=True를 명시하여 응답 스트림을 활성화
        with requests.post(OLLAMA_API_URL, json=payload, timeout=240, stream=True) as response:
            response.raise_for_status()

            # 응답 스트림을 라인 단위로 읽음
            for line in response.iter_lines():
                if line: # 빈 줄은 건너뜀
                    try:
                        # 각 라인이 JSON 객체라고 가정하고 파싱
                        json_data = json.loads(line.decode('utf-8'))

                        # Ollama 스트리밍 응답에서 'response' 필드에 실제 텍스트가 담겨있음
                        if 'response' in json_data:
                            full_ai_response_chunks.append(json_data['response'])
                        
                        # Ollama 스트리밍 응답의 마지막은 'done': true 필드를 포함함
                        if json_data.get('done', False):
                            logger.info("Ollama streaming response finished.")
                            break # 스트림 종료 신호가 오면 루프 종료
                        
                        # 오류 메시지가 포함된 청크가 올 수도 있으므로 처리
                        if 'error' in json_data:
                            logger.error(f"Ollama streaming error received: {json_data['error']}")
                            return f"Ollama 모델에서 스트리밍 오류가 발생했습니다: {json_data['error']}"

                    except json.JSONDecodeError as e:
                        logger.warning(f"Ollama 스트림에서 JSON 파싱 오류 발생: {e}. 문제의 라인: '{line.decode('utf-8')[:100]}...'")
                        # 불완전하거나 유효하지 않은 JSON 라인은 건너뛸 수 있습니다.
                        continue
                    except Exception as e:
                        logger.error(f"Ollama 스트림 처리 중 예상치 못한 오류 발생: {e}", exc_info=True)
                        continue
        
        # 모든 청크를 합쳐 최종 응답 문자열 생성
        final_response = "".join(full_ai_response_chunks).strip()
        if not final_response:
             logger.warning("Ollama streaming response returned no content.")
             return "죄송합니다. Ollama 모델로부터 응답을 받지 못했습니다."
        return final_response

    except requests.exceptions.ConnectionError:
        logger.error(f"오류: {OLLAMA_API_URL}의 Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인가요?", exc_info=True)
        return "죄송합니다. 도슨트 기능을 사용할 수 없습니다. 로컬 AI 서버에 연결할 수 없습니다."
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama 모델 호출 중 오류 발생: {e}", exc_info=True)
        return f"죄송합니다. 도슨트 기능을 사용하는 중 오류가 발생했습니다: {e}"
    except Exception as e:
        logger.critical(f"예상치 못한 오류 발생: {e}", exc_info=True)
        return "죄송합니다. 알 수 없는 오류가 발생했습니다."

