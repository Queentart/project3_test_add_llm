from rest_framework import serializers
from .models import Conversation, Message, GeneratedImage # GeneratedImage 모델 임포트

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['sender', 'text', 'timestamp', 'image_url']

class ConversationSerializer(serializers.ModelSerializer):
    # messages = MessageSerializer(many=True, read_only=True) # 필요 시 주석 해제하여 대화 내 메시지 포함 가능
    first_message_text = serializers.SerializerMethodField() # [추가됨] 첫 메시지 텍스트를 위한 필드

    class Meta:
        model = Conversation
        fields = ['session_id', 'created_at', 'summary', 'first_message_text'] # [수정됨] summary 필드 포함

    def get_first_message_text(self, obj):
        """
        대화의 첫 번째 사용자 메시지 내용을 반환합니다.
        대화 요약이 없는 경우에 대비하여 사용됩니다.
        """
        first_user_message = obj.messages.filter(sender='user').order_by('timestamp').first()
        if first_user_message:
            return first_user_message.text[:50] + '...' if len(first_user_message.text) > 50 else first_user_message.text
        return "새 대화" # [수정됨] 요약이 없는 경우 기본값

class GeneratedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = '__all__' # 모든 필드를 포함
