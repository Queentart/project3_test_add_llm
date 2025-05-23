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
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [os.path.join(BASE_DIR, 'templates')], # 프로젝트 루트의 'templates' 폴더를 추가
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                'django.template.context_processors.debug',
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

LANGUAGE_CODE = "ko-kr"

TIME_ZONE = "Asia/Seoul"

USE_I18N = True

USE_TZ = True

# --- Cache (Redis) Settings ---
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1', # 캐시용 DB 번호 (Redis가 0부터 15까지 지원)
        'TIMEOUT': 600, # 넉넉하게 10분 (초 단위)
    }
}


# --- Static and Media Files Settings ---
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

# Django가 정적 파일을 찾을 디렉토리 목록.
# 'templates'와 마찬가지로 프로젝트 루트에 있는 'static' 폴더를 명시적으로 추가합니다.
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# `python manage.py collectstatic` 명령 실행 시 정적 파일이 수집될 최종 디렉토리
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


MEDIA_URL = '/media/'
# 사용자 업로드 파일(ComfyUI input 포함) 및 생성된 이미지(ComfyUI output)가 저장될 루트 디렉토리
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# ComfyUI 관련 경로 설정 (views.py에서 사용)
COMFYUI_INPUT_DIR = os.path.join(MEDIA_ROOT, 'comfyui_input')
# COMFYUI_OUTPUT_DIR = os.path.join(MEDIA_ROOT, 'comfyui_output') # 이 변수는 views.py에서 직접 사용되지 않으므로 제거하거나 주석 처리해도 무방합니다.

# ComfyUI API URL 설정 (views.py에서 사용할 URL)
COMFYUI_API_URL = 'http://127.0.0.1:8188/prompt'
COMFYUI_HISTORY_URL = 'http://127.0.0.1:8188/history'
COMFYUI_IMAGE_URL = 'http://127.0.0.1:8188/view'


# 로깅 설정 (디버깅을 위해 DEBUG 레벨로 설정)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            # 여기서 settings.DEBUG 대신 그냥 DEBUG를 사용합니다.
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
            # 여기서 settings.DEBUG 대신 그냥 DEBUG를 사용합니다.
            'level': 'DEBUG' if DEBUG else 'INFO', # DEBUG 모드일 때 DEBUG 레벨, 아니면 INFO
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if DEBUG else 'simple', # 여기서도 DEBUG 사용
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
    }
}
# --- CORS (Cross-Origin Resource Sharing) Settings ---
# 'corsheaders' 앱을 설치해야 합니다: pip install django-cors-headers
# INSTALLED_APPS에 'corsheaders' 추가하고, MIDDLEWARE에 'corsheaders.middleware.CorsMiddleware' 추가
# 프론트엔드가 Django와 같은 도메인에서 서비스되므로 CORS는 엄밀히 필요 없지만,
# 개발 중이거나 추후 분리될 가능성을 대비하여 유지할 수 있습니다.
# 운영 환경에서는 반드시 CORS_ALLOWED_ORIGINS를 사용하여 특정 도메인만 허용해야 합니다.
CORS_ALLOW_ALL_ORIGINS = True 
# CORS_ALLOWED_ORIGINS = [
#     "http://127.0.0.1:8000", # Django 개발 서버 주소
# ]


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"