import json
import urllib.request
import urllib.parse
import uuid # 고유한 client_id 생성을 위해

# 1. ComfyUI API 서버 주소 설정
# ComfyUI를 실행한 서버의 IP 주소와 포트를 입력하세요.
# 기본값은 127.0.0.1:8188 (로컬 호스트) 입니다.
server_address = "127.0.0.1:8188"
client_id = str(uuid.uuid4()) # 각 요청을 구분하기 위한 고유한 클라이언트 ID

def queue_prompt(prompt_workflow_json_data):
    """
    ComfyUI 서버로 JSON 워크플로우 데이터를 전송하여 실행을 큐에 추가합니다.
    """
    p = {"prompt": prompt_workflow_json_data, "client_id": client_id}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{server_address}/prompt", data=data)
    try:
        response = urllib.request.urlopen(req)
        return json.loads(response.read())
    except urllib.error.URLError as e:
        print(f"Error connecting to ComfyUI server: {e.reason}")
        print("Please ensure ComfyUI server is running at", server_address)
        return None

# 2. Python 코드 내에 워크플로우 JSON 문자열 정의
# 사용자께서 제공해주신 JSON 데이터를 그대로 사용합니다.
prompt_text = """
{
  "1": {
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    },
    "class_type": "CheckpointLoaderSimple",
    "_meta": {
      "title": "체크포인트 로드"
    }
  },
  "2": {
    "inputs": {
      "width": 512,
      "height": 512,
      "batch_size": 1
    },
    "class_type": "EmptyLatentImage",
    "_meta": {
      "title": "빈 잠재 이미지"
    }
  },
  "3": {
    "inputs": {
      "ipadapter_file": "ip-adapter-plus_sdxl_vit-h.safetensors"
    },
    "class_type": "IPAdapterModelLoader",
    "_meta": {
      "title": "IPAdapter Model Loader"
    }
  },
  "4": {
    "inputs": {
      "clip_name": "SDXLopen_clip_pytorch_model_vit_h.safetensors"
    },
    "class_type": "CLIPVisionLoader",
    "_meta": {
      "title": "CLIP_VISION 로드"
    }
  },
  "5": {
    "inputs": {
      "seed": 843555816917503,
      "steps": 20,
      "cfg": 8,
      "sampler_name": "euler",
      "scheduler": "normal",
      "denoise": 1,
      "model": [
        "7",
        0
      ],
      "positive": [
        "11",
        0
      ],
      "negative": [
        "10",
        0
      ],
      "latent_image": [
        "2",
        0
      ]
    },
    "class_type": "KSampler",
    "_meta": {
      "title": "KSampler"
    }
  },
  "6": {
    "inputs": {
      "samples": [
        "5",
        0
      ],
      "vae": [
        "1",
        2
      ]
    },
    "class_type": "VAEDecode",
    "_meta": {
      "title": "VAE 디코드"
    }
  },
  "7": {
    "inputs": {
      "weight": 1.0000000000000002,
      "weight_type": "linear",
      "combine_embeds": "concat",
      "start_at": 0,
      "end_at": 1,
      "embeds_scaling": "V only",
      "model": [
        "1",
        0
      ],
      "ipadapter": [
        "3",
        0
      ],
      "image": [
        "9",
        0
      ],
      "attn_mask": [
        "9",
        1
      ],
      "clip_vision": [
        "4",
        0
      ]
    },
    "class_type": "IPAdapterAdvanced",
    "_meta": {
      "title": "IPAdapter Advanced"
    }
  },
  "8": {
    "inputs": {
      "filename_prefix": "transferred_image",
      "images": [
        "6",
        0
      ]
    },
    "class_type": "SaveImage",
    "_meta": {
      "title": "이미지 저장"
    }
  },
  "9": {
    "inputs": {
      "image": "koyoonjeong.jpg"
    },
    "class_type": "LoadImage",
    "_meta": {
      "title": "이미지 로드"
    }
  },
  "10": {
    "inputs": {
      "system_prompt": "superior",
      "user_prompt": "Cartoonish, chibi, overly simplistic, unrealistic proportions, child-like drawing, sketchy lines, rough edges, pixelated, low quality, blurry, distorted, Multiple characters, crowded background, distracting elements, too busy, ugly background, deformed hands, extra limbs, disfigured face, unnatural pose.",
      "clip": [
        "1",
        1
      ]
    },
    "class_type": "CLIPTextEncodeLumina2",
    "_meta": {
      "title": "CLIP 텍스트 인코딩 (Lumina2)"
    }
  },
  "11": {
    "inputs": {
      "system_prompt": "superior",
      "user_prompt": "A mesmerizingly beautiful South Korean woman, inspired by the delicate features and graceful charm of Go Youn-jung, reimagined as a **realistic 3D Disney heroine**. Rendered in the distinct animation style of modern Disney movies like **Frozen, Tangled, or Moana**. Extremely high detail, cinematic lighting, volumetric light, soft shadows, intricate textures, hyperrealistic rendering, octane render, cinematic still, studio quality, ultra high definition, 8K. **NOT 2D, NOT flat, NOT cartoon, NOT anime, NOT manga, NOT cel-shaded, NOT illustrated.** She possesses **expressive, large Disney eyes with sparkling irises**, long flowing hair with natural movement, and a gentle, confident expression. The art style emphasizes **smooth, rendered surfaces with subtle facial nuances and lifelike skin texture**, showcasing a perfect blend of realism and animated charm. Solo character, full-body shot, graceful and dynamic pose, enchanting atmosphere, warm and inviting color palette, dreamlike background, fairytale setting. Wearing an elegant, flowing gown.",
      "clip": [
        "1",
        1
      ]
    },
    "class_type": "CLIPTextEncodeLumina2",
    "_meta": {
      "title": "CLIP 텍스트 인코딩 (Lumina2)"
    }
  }
}
"""

# 3. JSON 문자열을 파이썬 딕셔너리로 파싱
prompt_workflow_data = json.loads(prompt_text)

# 4. 파라미터 동적 변경 (사용자 입력 예시)
# 장고 뷰에서 사용자 입력을 받아 이곳의 변수를 업데이트합니다.

# 긍정 프롬프트 업데이트 (노드 ID 11)
# 이전에 제안했던 디즈니 스타일 프롬프트를 적용합니다.
new_positive_prompt = "A stunningly beautiful Korean woman, inspired by Go Youn-jung's delicate features and elegant charm, reimagined as a realistic Disney heroine, in the distinct 3D animation style of modern Disney movies like Frozen or Tangled. Extremely high detail, cinematic lighting, volumetric light, soft shadows, intricate textures, hyperrealistic rendering, octane render, cinematic still, studio quality, ultra high definition, 4K. She has expressive, large Disney eyes with sparkling irises, long flowing hair with natural movement, and a gentle, confident expression. The art style emphasizes smooth, rendered surfaces rather than flat cel-shading, with subtle facial nuances and lifelike skin texture. Solo character, full-body shot, graceful pose, enchanting atmosphere, warm color palette, dreamlike background, fairytale setting."
prompt_workflow_data["11"]["inputs"]["user_prompt"] = new_positive_prompt

# 부정 프롬프트 업데이트 (노드 ID 10)
new_negative_prompt = "Cartoonish, chibi, overly simplistic, unrealistic proportions, child-like drawing, sketchy lines, rough edges, pixelated, low quality, blurry, distorted, Multiple characters, crowded background, distracting elements, too busy, ugly background, deformed hands, extra limbs, disfigured face, unnatural pose."
prompt_workflow_data["10"]["inputs"]["user_prompt"] = new_negative_prompt

# KSampler denoising strength 설정 (노드 ID 5)
# 이미지-투-이미지 변환에 맞게 denoise 값을 조절합니다.
new_denoise_strength = 0.7 # 0.6에서 0.8 사이의 값으로 조절하며 테스트해보세요.
prompt_workflow_data["5"]["inputs"]["denoise"] = new_denoise_strength

# KSampler Seed 값 변경 (노드 ID 5)
# 매번 다른 결과를 얻기 위해 random seed를 사용하거나, 특정 시드를 지정할 수 있습니다.
# 여기서는 예시로 랜덤 시드를 사용합니다.
prompt_workflow_data["5"]["inputs"]["seed"] = json.loads("843555816917503") # ComfyUI 랜덤 시드 설정
# prompt_workflow_data["5"]["inputs"]["seed"] = 12345 # 특정 시드 지정 시

# LoadImage 노드의 이미지 파일명 변경 (노드 ID 9)
# 사용자가 업로드한 이미지 파일명으로 변경해야 합니다.
# 예시: 'uploaded_koyoonjeong_new.jpg'
prompt_workflow_data["9"]["inputs"]["image"] = "koyoonjeong.jpg" # 실제 업로드된 파일명으로 변경 필요

# IPAdapterAdvanced의 weight 조정 (노드 ID 7)
# IP-Adapter의 영향력을 조절합니다.
prompt_workflow_data["7"]["inputs"]["weight"] = 1.0 # 0.8 ~ 1.2 사이에서 조절

# EmptyLatentImage의 해상도 조절 (노드 ID 2)
# IP-Adapter는 원본 이미지의 해상도에 크게 영향을 받지 않지만,
# SDXL은 1024x1024에 최적화되어 있으므로, 512x512에서 1024x1024로 변경하는 것을 고려해보세요.
prompt_workflow_data["2"]["inputs"]["width"] = 1024
prompt_workflow_data["2"]["inputs"]["height"] = 1024


# 5. 워크플로우 실행
print("ComfyUI 워크플로우를 실행합니다...")
results = queue_prompt(prompt_workflow_data)

if results:
    print("워크플로우가 성공적으로 큐에 추가되었습니다.")
    print("Prompt ID:", results.get("prompt_id"))
    print(f"생성된 이미지는 ComfyUI 서버의 output 폴더에 'transferred_image_...' 형태로 저장됩니다.")
    # 실제 장고 연동 시에는 여기서 생성된 이미지의 경로를 추적하여 사용자에게 반환하는 로직이 추가됩니다.
else:
    print("워크플로우 실행에 실패했습니다. ComfyUI 서버가 올바르게 실행 중인지 확인하세요.")