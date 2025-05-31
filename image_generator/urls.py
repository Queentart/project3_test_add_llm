# image_generator/urls.py (앱 레벨 URL)
from django.urls import path, include # include 임포트 추가
from . import views # 이 앱의 views.py에서 뷰 함수들을 임포트합니다.
from django.conf import settings # MEDIA_URL 설정을 위함
from django.conf.urls.static import static # MEDIA_ROOT 설정을 위함

urlpatterns = [
    # HTML 페이지 뷰 (템플릿의 {% url %} 태그와 일치하도록 이름 변경)
    path('', views.welcome_view, name='welcome_page'), # 'welcome' -> 'welcome_page'
    path('features/', views.features_view, name='features_page'), # 'features' -> 'features_page'
    path('about/', views.about_view, name='about_page'),     # 'about' -> 'about_page'
    path('main/', views.main_view, name='main_page'),         # 'main' -> 'main_page'
    path("gallery/", views.gallery_view, name='gallery_page'),
    path("archive/", views.archive_view, name='archive_page'),
    path('api/images/', views.api_get_images, name='api_images'),
    # path('api/museums/', views.museum_list_api, name='api_museums'),

    # API 엔드포인트 (기존 이름 유지)
    path('api/process_request/', views.process_request_api, name='process_request_api'),
    # [추가됨] 이미지 생성 작업 상태 확인 API 엔드포인트
    # <uuid:task_id>는 UUID 형식의 task_id를 캡처합니다.
    path('api/tasks/<uuid:task_id>/status/', views.check_task_status_api, name='check_task_status'),
    path('api/conversations/', views.get_conversations_api, name='api_conversations'),
    path('api/conversations/<uuid:conversation_id>/', views.get_conversation_history_api, name='api_conversation_history'),
    # [재추가됨] delete_oldest_conversations_api 함수 경로
    path('api/conversations/delete_oldest/', views.delete_oldest_conversations_api, name='api_delete_oldest_conversations'),
]

# 개발 환경에서 미디어 파일 서빙을 위한 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
