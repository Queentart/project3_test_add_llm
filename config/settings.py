# your_django_project/config/settings.py

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-&i&@li!b%1x#dd#$+@pi#$8(1&6#nxiu*s_w&&k=9ucl3lktlp"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    'rest_framework',
    'image_generator', # 당신의 앱 이름이 'image_generator'임을 확인했습니다.
    'corsheaders', # CORS 설정을 위해 추가
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # CORS 미들웨어는 CommonMiddleware 위에 위치해야 합니다.
    'corsheaders.middleware.CorsMiddleware', # CORS 미들웨어 추가
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # templates 디렉토리의 위치를 명시적으로 지정
        "DIRS": [os.path.join(BASE_DIR, 'templates')], # <--- 이 부분이 수정되었습니다.
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "ko-kr" # 한국어 설정

TIME_ZONE = "Asia/Seoul" # 한국 시간대 설정

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "/static/"
# 개발 환경에서 static 파일이 어디에 있는지 Django에게 알려줍니다.
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"), # <--- 이 부분이 수정되었습니다.
]

# Media files (User uploaded content)
# 유저가 업로드하는 이미지 파일 등을 저장할 경로
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media", "comfyui_output") # <--- 이 부분이 수정되었습니다.

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- ComfyUI API Settings ---
# ComfyUI가 실행 중인 주소로 변경하세요.
# 기본값은 로컬호스트 8188 포트입니다.
COMFYUI_API_URL = "http://127.0.0.1:8188/prompt"
COMFYUI_HISTORY_URL = "http://127.0.0.1:8188/history"
COMFYUI_IMAGE_URL = "http://127.0.0.1:8188/view"
# ComfyUI의 'input' 폴더의 실제 경로를 지정합니다.
# **이 경로는 ComfyUI가 설치된 디렉토리 내의 'input' 폴더여야 합니다.**
# 예: "C:\\Users\\YourUser\\ComfyUI\\input" (Windows)
# 예: "/home/youruser/ComfyUI/input" (Linux)
# 개발 환경에 맞춰 정확히 수정해야 합니다.
COMFYUI_INPUT_DIR = os.path.join(BASE_DIR, 'comfyui_data', 'input') # <--- 이 부분이 가장 중요합니다!

# --- Ollama API Settings ---
# Ollama가 실행 중인 주소와 사용할 모델을 설정합니다.
# gemma_service.py에서 이 설정을 가져다 사용합니다.
OLLAMA_API_URL = "http://localhost:11434/api/generate" # Ollama API 엔드포인트
OLLAMA_MODEL_NAME = "gemma3:latest" # Ollama에 pull한 Gemma 모델 이름

# --- Cache Settings (Django Cache Framework) ---
# 이미지 생성 상태 및 대화 기록을 임시 저장하는 데 사용됩니다.
# 개발 환경에서는 로컬 메모리 캐시를 사용합니다.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake', # 캐시 이름을 고유하게 지정
    }
}

# --- Logging Settings ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO', # DEBUG 모드일 때 DEBUG 레벨, 아니면 INFO
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG', # 모든 로거의 기본 레벨을 DEBUG로 설정
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'), # Django 자체 로그는 INFO 레벨
            'propagate': False,
        },
        'image_generator': { # image_generator 앱의 로거
            'handlers': ['console'],
            'level': 'DEBUG', # 이 앱의 로그는 DEBUG 레벨로 출력
            'propagate': False,
        },
        # Ollama 서비스의 로깅도 추가 (만약 별도 로거가 필요하다면)
        'llm_cores': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}

# --- CORS (Cross-Origin Resource Sharing) Settings ---
CORS_ALLOW_ALL_ORIGINS = True # 개발용: 모든 출처 허용. 운영 환경에서는 특정 도메인으로 제한해야 합니다.
CORS_ALLOW_CREDENTIALS = True # 쿠키를 포함한 요청 허용 (CSRF 토큰 처리에 필요)

# CORS_ALLOWED_ORIGINS = [
#     "http://localhost:8000", # Django 개발 서버
#     "http://127.0.0.1:8000",
#     # 여기에 프론트엔드가 서비스되는 도메인을 추가하세요.
#     # 예: "http://yourfrontend.com"
# ]