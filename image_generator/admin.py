from django.contrib import admin
from .models import GeneratedImage, Conversation, Message # Message 모델도 임포트

# GeneratedImage 모델의 관리자 설정
@admin.register(GeneratedImage)
class GeneratedImageAdmin(admin.ModelAdmin):
    # list_display: 관리자 목록 페이지에 표시될 필드들
    # 'source_type' 대신 'image_type'과 'is_showcase'를 사용합니다.
    list_display = ('title', 'image_type', 'style', 'is_showcase', 'created_at', 'views', 'likes')
    
    # list_filter: 관리자 목록 페이지의 사이드바 필터에 표시될 필드들
    # 'source_type' 대신 'image_type'과 'is_showcase'를 사용합니다.
    list_filter = ('image_type', 'style', 'is_showcase')
    
    # search_fields: 검색 기능을 제공할 필드들
    search_fields = ('title', 'prompt', 'description')
    
    # readonly_fields: 관리자 페이지에서 수정할 수 없는 필드들
    readonly_fields = ('created_at', 'views', 'likes')

# Conversation 모델의 관리자 설정
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    # list_display: 관리자 목록 페이지에 표시될 필드들
    # 'summary' 필드는 모델에 없으므로, 대신 첫 메시지 미리보기를 위한 메서드를 사용합니다.
    list_display = ('session_id', 'created_at', 'get_first_message_preview')
    
    # list_filter: 대화 생성 날짜로 필터링
    list_filter = ('created_at',)
    
    # search_fields: 세션 ID로 검색 가능
    search_fields = ('session_id',)
    
    # readonly_fields: 세션 ID와 생성 날짜는 수정 불가
    readonly_fields = ('session_id', 'created_at')

    def get_first_message_preview(self, obj):
        """
        대화의 첫 번째 메시지 내용을 미리보기로 반환합니다.
        이는 'summary' 필드 대신 사용되어 오류를 해결합니다.
        """
        first_message = obj.messages.order_by('timestamp').first()
        return first_message.text[:50] + '...' if first_message and first_message.text else '새 대화'
    
    # 관리자 페이지에서 이 메서드의 컬럼 이름을 설정합니다.
    get_first_message_preview.short_description = '첫 메시지 미리보기'

# Message 모델의 관리자 설정 (선택 사항: 메시지 하나하나를 관리자에서 볼 필요가 없다면 등록하지 않아도 됨)
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    # list_display: 메시지 목록에 표시될 필드들
    list_display = ('conversation', 'sender', 'display_text_preview', 'timestamp', 'image_url')
    
    # list_filter: 발신자, 타임스탬프로 필터링
    list_filter = ('sender', 'timestamp')
    
    # search_fields: 메시지 내용으로 검색
    search_fields = ('text',)
    
    # readonly_fields: 타임스탬프와 이미지 URL은 수정 불가
    readonly_fields = ('timestamp', 'image_url')

    def display_text_preview(self, obj):
        """
        메시지 내용을 100자 이내로 잘라서 미리보기로 반환합니다.
        """
        return obj.text[:100] + '...' if len(obj.text) > 100 else obj.text
    
    display_text_preview.short_description = '내용'

