from django.db import models
from django.utils import timezone

class GeneratedImage(models.Model):
    # image_file = models.ImageField(upload_to='generated_images/')
    image_file = models.ImageField(upload_to='comfyui_output/') # 이 부분을 수정!

    title = models.CharField(max_length=200, verbose_name="이미지 제목")
    description = models.TextField(blank=True, verbose_name="설명")
    prompt = models.TextField(verbose_name="생성 프롬프트")
    style = models.CharField(max_length=100, verbose_name="스타일 (예: cyberpunk, oriental, 3d)")
    
    image_type = models.CharField(max_length=10, choices=[('t2i', 'Text-to-Image'), ('i2i', 'Image-to-Image')], default='t2i')

    created_at = models.DateTimeField(default=timezone.now, verbose_name="생성 날짜")
    views = models.PositiveIntegerField(default=0, verbose_name="조회수")
    likes = models.PositiveIntegerField(default=0, verbose_name="좋아요 수")

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "생성 이미지"
        verbose_name_plural = "생성 이미지들"
        ordering = ['-created_at']