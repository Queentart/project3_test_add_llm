# D:\project3_django_no_celery\config\urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView # 이 줄을 추가합니다.
from django.conf import settings
from django.conf.urls.static import static

# image_generator.views에서 index_view는 더 이상 임포트하지 않습니다.
from image_generator.views import generate_image_view, check_image_status_view

urlpatterns = [
    path("admin/", admin.site.urls),
    # 루트 URL ("/") 요청이 templates/index.html 파일을 렌더링하도록 변경
    # name='home'은 선택 사항이지만, 템플릿에서 URL을 참조할 때 유용합니다.
    path("", TemplateView.as_view(template_name='index.html'), name='home'),

    # API 엔드포인트는 그대로 유지
    path("api/generate-image/", generate_image_view, name="generate_image"),
    path("api/task-status/<uuid:task_id>/", check_image_status_view, name="check_image_status"),
]

# 개발 서버에서 미디어 파일 서빙을 위한 설정 추가
# DEBUG=True 일 때만 작동합니다. 배포 시에는 웹 서버(Nginx/Apache)가 처리해야 합니다.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)