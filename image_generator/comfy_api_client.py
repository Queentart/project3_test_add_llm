# image_generator/comfy_api_client.py

import json
import requests
import uuid
import os
import time

# 웹소켓 관련 라이브러리 (get_image_from_ws 함수를 다시 활성화할 경우 필요)
# import websocket
# import io
# from PIL import Image
# import base64 # image_to_base64 함수로 대체됨

class ComfyAPIClient:
    def __init__(self, host):
        """
        ComfyUI API 클라이언트를 초기화합니다.
        :param host: ComfyUI 서버의 주소 (예: "http://127.0.0.1:8188")
        """
        self.host = host
        # 웹소켓 연결 시 사용되는 클라이언트 ID (현재 버전에서는 직접 사용 안함)
        self.client_id = str(uuid.uuid4())

    def queue_prompt(self, prompt_workflow):
        """
        ComfyUI에 워크플로우를 큐에 추가하고 실행을 요청합니다.
        :param prompt_workflow: ComfyUI 워크플로우 JSON 데이터 (딕셔너리 형태).
                                이 딕셔너리는 반드시 최상위 'prompt' 키를 포함해야 합니다.
                                예: {"prompt": { "3": {...}, "4": {...} }}
        :return: ComfyUI API의 응답 (주로 prompt_id를 포함하는 딕셔너리)
        """
        url = f"{self.host}/prompt"
        headers = {'Content-Type': 'application/json'}

        # prompt_workflow 자체가 이미 {"prompt": ...} 형태를 가지고 있어야 합니다.
        # 따라서, data 딕셔너리에서 prompt_workflow를 직접 prompt 값으로 사용합니다.
        data = {
            "prompt": prompt_workflow,
            "client_id": self.client_id
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=120) # 타임아웃을 넉넉히 늘림
            response.raise_for_status() # 4xx 또는 5xx HTTP 에러 발생 시 예외 발생

            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"ComfyUI queue_prompt 요청 오류: {e}")
            if response is not None:
                print(f"응답 상태 코드: {response.status_code}")
                print(f"응답 본문: {response.text[:500]}...") # 응답의 일부를 출력
            raise Exception(f"ComfyUI 서버 통신 오류: {e}")
        except json.JSONDecodeError as e:
            print(f"ComfyUI queue_prompt JSON 파싱 오류: {e}")
            if response is not None:
                print(f"ComfyUI 서버 원본 응답: {response.text[:500]}...")
            raise Exception(f"ComfyUI 응답 데이터 파싱 오류: {e}")
        except Exception as e:
            print(f"queue_prompt에서 예상치 못한 오류 발생: {e}")
            raise Exception(f"예상치 못한 오류: {e}")

    def get_history(self, prompt_id):
        """
        특정 prompt_id에 대한 ComfyUI의 실행 이력을 조회합니다.
        :param prompt_id: 조회할 프롬프트 ID
        :return: ComfyUI의 실행 이력 데이터 (딕셔너리 형태)
        """
        url = f"{self.host}/history/{prompt_id}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ComfyUI get_history 요청 오류: {e}")
            raise Exception(f"ComfyUI 이력 조회 통신 오류: {e}")
        except json.JSONDecodeError as e:
            print(f"ComfyUI get_history JSON 파싱 오류: {e}")
            if response is not None:
                print(f"ComfyUI 서버 원본 응답: {response.text[:500]}...")
            raise Exception(f"ComfyUI 이력 응답 파싱 오류: {e}")
        except Exception as e:
            print(f"get_history에서 예상치 못한 오류 발생: {e}")
            raise Exception(f"예상치 못한 오류: {e}")

    def get_image(self, filename, subfolder, folder_type):
        """
        ComfyUI 서버에서 이미지를 다운로드합니다.
        :param filename: 이미지 파일 이름
        :param subfolder: 이미지 서브 폴더 (예: "ComfyUI/output/")
        :param folder_type: 폴더 타입 (예: "output", "input", "temp")
        :return: 이미지의 바이너리 데이터
        """
        url = f"{self.host}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": folder_type
        }
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.content # 이미지 바이너리 데이터 반환
        except requests.exceptions.RequestException as e:
            print(f"ComfyUI get_image 요청 오류: {e}")
            raise Exception(f"ComfyUI 이미지 다운로드 통신 오류: {e}")
        except Exception as e:
            print(f"get_image에서 예상치 못한 오류 발생: {e}")
            raise Exception(f"예상치 못한 오류: {e}")

    def upload_image(self, image_path, image_type="input", overwrite=True):
        """
        로컬 이미지를 ComfyUI 서버로 업로드합니다.
        :param image_path: 업로드할 로컬 이미지 파일 경로
        :param image_type: ComfyUI 서버의 저장 위치 (예: "input", "temp")
        :param overwrite: 기존 파일이 있을 경우 덮어쓸지 여부
        :return: ComfyUI API의 이미지 업로드 응답 (딕셔너리)
        """
        url = f"{self.host}/upload/image"
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"업로드할 이미지를 찾을 수 없습니다: {image_path}")

        files = {
            'image': (os.path.basename(image_path), open(image_path, 'rb'), 'application/octet-stream'),
        }
        data = {
            'type': image_type,
            'overwrite': 'true' if overwrite else 'false'
        }

        try:
            response = requests.post(url, files=files, data=data, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"ComfyUI upload_image 요청 오류: {e}")
            raise Exception(f"ComfyUI 이미지 업로드 통신 오류: {e}")
        except json.JSONDecodeError as e:
            print(f"ComfyUI upload_image JSON 파싱 오류: {e}")
            if response is not None:
                print(f"ComfyUI 서버 원본 응답: {response.text[:500]}...")
            raise Exception(f"ComfyUI 업로드 응답 파싱 오류: {e}")
        except Exception as e:
            print(f"upload_image에서 예상치 못한 오류 발생: {e}")
            raise Exception(f"예상치 못한 오류: {e}")


def load_workflow_json(file_path):
    """
    지정된 경로에서 ComfyUI 워크플로우 JSON 파일을 로드합니다.
    :param file_path: 워크플로우 JSON 파일의 전체 경로
    :return: 파싱된 워크플로우 딕셔너리. 이 딕셔너리는 ComfyUI API 형식이어야 합니다
             (즉, 최상위에 'prompt' 키를 포함해야 합니다).
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"워크플로우 파일을 찾을 수 없습니다: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            workflow_data = json.load(f)
        print(f"Successfully loaded workflow from: {file_path}")
        print(f"Type of loaded workflow_data: {type(workflow_data)}")
        
        # ComfyUI API 형식은 최상위 딕셔너리에 'prompt' 키 아래에 노드들이 존재합니다.
        # 만약 로드된 JSON이 'prompt' 키를 직접 포함하지 않는다면, 오류를 발생시킵니다.
        # (이것은 "Save (API format)"으로 저장된 파일이 아니라는 의미이므로, 오류를 명확히 함)
        if not isinstance(workflow_data, dict) or 'prompt' not in workflow_data:
            raise ValueError(
                f"로드된 워크플로우 JSON은 ComfyUI API 형식이 아닙니다. 'prompt' 키가 최상위에 존재해야 합니다. "
                f"파일: {file_path}. 실제 최상위 키: {workflow_data.keys() if isinstance(workflow_data, dict) else 'Not a dict'}"
            )
        print(f"Workflow contains 'prompt' key. Number of nodes: {len(workflow_data['prompt'])}")
        return workflow_data
    except json.JSONDecodeError as e:
        raise ValueError(f"워크플로우 JSON 파일 파싱 오류: {file_path} - 파일 형식이 올바른 JSON이 아닙니다. {e}")
    except Exception as e:
        raise Exception(f"워크플로우 파일 로드 중 알 수 없는 오류: {file_path} - {e}")


def update_workflow_node_input(workflow, node_id, input_name, new_value):
    """
    워크플로우 딕셔너리에서 특정 노드의 입력을 업데이트합니다.
    이 함수는 workflow가 이미 ComfyUI API 형식 (즉, 'prompt' 키를 포함하는)이라고 가정합니다.
    :param workflow: 업데이트할 ComfyUI API 워크플로우 딕셔너리 (prompt 키 포함)
    :param node_id: 업데이트할 노드의 ID (문자열)
    :param input_name: 업데이트할 입력의 이름 (예: "text", "seed", "image")
    :param new_value: 새로 설정할 값
    :return: 업데이트된 워크플로우 딕셔너리
    """
    # 이미 load_workflow_json에서 'prompt' 키 존재 여부를 확인하므로, 여기서는 간략화합니다.
    # 만약 이 함수가 'prompt' 키가 없는 워크플로우를 받을 수 있다면, 다시 아래 검사를 추가해야 합니다.
    # 현재는 'load_workflow_json'이 API 형식을 보장하므로, 'workflow['prompt']'를 직접 접근합니다.
    
    if node_id in workflow['prompt']:
        node_data = workflow['prompt'][node_id]
        if 'inputs' in node_data:
            node_data['inputs'][input_name] = new_value
            print(f"노드 {node_id}의 입력 '{input_name}'을 '{new_value}'로 업데이트했습니다.")
        else:
            print(f"경고: 노드 {node_id}에 'inputs' 키가 없습니다. 업데이트할 수 없습니다.")
    else:
        print(f"경고: 워크플로우에서 노드 ID {node_id}를 찾을 수 없습니다. 업데이트할 수 없습니다.")
    return workflow


def find_node_id_by_class_type(workflow_api_format, target_class_type, hint=None):
    """
    ComfyUI API 형식의 워크플로우 JSON에서 특정 class_type을 가진 노드의 ID를 찾습니다.
    'hint'가 'positive' 또는 'negative'인 경우, KSampler 노드와의 연결을 통해 CLIPTextEncode 노드를 찾습니다.
    
    :param workflow_api_format: ComfyUI API 형식의 워크플로우 딕셔너리 (최상위 'prompt' 키 포함)
    :param target_class_type: 찾을 노드의 class_type (예: "CLIPTextEncode", "KSampler")
    :param hint: CLIPTextEncode 노드일 경우 "positive" 또는 "negative" 힌트
    :return: 찾은 노드의 ID (문자열), 없으면 None
    """
    # API 형식 워크플로우에서 실제 노드 데이터는 'prompt' 키 아래에 있습니다.
    nodes = workflow_api_format.get("prompt")
    if not nodes:
        print("워크플로우 JSON에 'prompt' 키가 없거나 비어 있습니다. 노드를 찾을 수 없습니다.")
        return None

    if target_class_type == "CLIPTextEncode" and hint:
        ksampler_node_id = None
        # KSampler 노드를 먼저 찾습니다.
        for node_id, node_data in nodes.items():
            if node_data.get("class_type") == "KSampler":
                ksampler_node_id = node_id
                break

        if ksampler_node_id:
            ksampler_node = nodes.get(ksampler_node_id)
            if hint == "positive":
                # KSampler의 'positive' 입력이 연결된 노드 ID 반환
                if "positive" in ksampler_node.get("inputs", {}) and isinstance(ksampler_node["inputs"]["positive"], list):
                    connected_node_id = str(ksampler_node["inputs"]["positive"][0]) # 노드 ID를 문자열로 명시
                    if nodes.get(connected_node_id, {}).get("class_type") == "CLIPTextEncode":
                        print(f"찾은 긍정 프롬프트 노드 ID: {connected_node_id}")
                        return connected_node_id
            elif hint == "negative":
                # KSampler의 'negative' 입력이 연결된 노드 ID 반환
                if "negative" in ksampler_node.get("inputs", {}) and isinstance(ksampler_node["inputs"]["negative"], list):
                    connected_node_id = str(ksampler_node["inputs"]["negative"][0]) # 노드 ID를 문자열로 명시
                    if nodes.get(connected_node_id, {}).get("class_type") == "CLIPTextEncode":
                        print(f"찾은 부정 프롬프트 노드 ID: {connected_node_id}")
                        return connected_node_id
            print(f"KSampler에 연결된 {hint} CLIPTextEncode 노드를 찾을 수 없습니다.")
            return None
        else:
            print("워크플로우에서 KSampler 노드를 찾을 수 없습니다.")
            return None
    else:
        # CLIPTextEncode가 아니거나 힌트가 지정되지 않은 경우, 단순히 class_type으로 찾기
        for node_id, node_data in nodes.items():
            if node_data.get("class_type") == target_class_type:
                print(f"찾은 노드 (class_type: {target_class_type}): {node_id}")
                return node_id
    
    print(f"{target_class_type} 노드를 찾을 수 없습니다.")
    return None

# # 이미지 파일을 Base64로 인코딩하는 헬퍼 함수 (필요시 사용, 현재는 upload_image 함수가 더 편리)
# def image_to_base64(image_path):
#     import base64
#     with open(image_path, "rb") as f:
#         return base64.b64encode(f.read()).decode("utf-8")