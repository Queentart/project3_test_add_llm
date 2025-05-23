# D:\project3_django\image_generator\urls.py
from django.urls import path
from .views import generate_image_view
from .views import index_view

urlpatterns = [
    # 'generate/' 대신 'generate-image/'로 변경
    path('generate-image/', generate_image_view, name='generate_image_api'), # API 호출용
    path('', index_view, name='home'), # 폼 페이지 렌더링용
]