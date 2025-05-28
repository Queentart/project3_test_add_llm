# config/urls.py
from django.contrib import admin
from django.urls import path, include # `include` 함수를 사용하려면 이 부분을 임포트해야 합니다.
from django.conf import settings
from django.conf.urls.static import static # static/media 파일 서빙을 위해 필요합니다.

urlpatterns = [
    path("admin/", admin.site.urls), # Django 관리자 페이지

    # 'image_generator' 앱의 모든 URL을 루트 경로에 포함합니다.
    # 이렇게 하면 'image_generator/urls.py'에 정의된
    # 모든 path (예: '', 'features/', 'main/', 'api/process_request/' 등)가
    # 자동으로 이 프로젝트의 루트 URL에서부터 시작하여 매핑됩니다.
    path('', include('image_generator.urls')),

    # 개발 환경에서만 정적(STATIC_URL) 및 미디어(MEDIA_URL) 파일 서빙을 처리합니다.
    # 이 설정은 프로젝트의 루트 urls.py에 있어야 합니다.
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # 정적 파일 서빙도 추가