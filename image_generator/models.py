from django.db import models
from django.utils import timezone
import uuid # UUID 필드를 위해 임포트

class GeneratedImage(models.Model):
    image_file = models.ImageField(upload_to='comfyui_output/')
    title = models.CharField(max_length=200, verbose_name="이미지 제목")
    description = models.TextField(blank=True, verbose_name="설명")
    prompt = models.TextField(verbose_name="생성 프롬프트")
    style = models.CharField(max_length=100, verbose_name="스타일 (예: cyberpunk, oriental, 3d)")
    
    image_type = models.CharField(max_length=10, choices=[('t2i', 'Text-to-Image'), ('i2i', 'Image-to-Image')], default='t2i')

    created_at = models.DateTimeField(default=timezone.now, verbose_name="생성 날짜")
    views = models.PositiveIntegerField(default=0, verbose_name="조회수")
    likes = models.PositiveIntegerField(default=0, verbose_name="좋아요 수")
    is_showcase = models.BooleanField(default=False, verbose_name="갤러리 전시 여부") # 새로 추가된 필드

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "생성 이미지"
        verbose_name_plural = "생성 이미지들"
        ordering = ['-created_at']

# Conversation 모델
class Conversation(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="세션 ID")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성 날짜")
    summary = models.CharField(max_length=255, blank=True, verbose_name="대화 요약") # [추가됨] 대화 요약 필드
    # [추가] start_time 필드 추가
    start_time = models.DateTimeField(default=timezone.now, verbose_name="대화 시작 시간")

    def __str__(self):
        # [수정] summary 필드를 반환하여 대화 요약이 명확하게 표시되도록 함
        return self.summary if self.summary else f"Conversation {self.session_id}"

    class Meta:
        verbose_name = "대화"
        verbose_name_plural = "대화들"
        ordering = ['-created_at']

# Message 모델
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE, verbose_name="대화")
    sender = models.CharField(max_length=10, choices=[('user', '사용자'), ('ai', 'AI')], verbose_name="발신자")
    text = models.TextField(verbose_name="내용")
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="타임스탬프")
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="이미지 URL") # 이미지 URL 필드 추가
    # [추가] image_file_path 필드 추가 (views.py에서 사용됨)
    image_file_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="이미지 파일 경로")

    def __str__(self):
        return f"{self.sender} at {self.timestamp}: {self.text[:50]}"

    class Meta:
        verbose_name = "메시지"
        verbose_name_plural = "메시지들"
        ordering = ['timestamp']
