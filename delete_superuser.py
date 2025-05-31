from django.contrib.auth import get_user_model
User = get_user_model()

# 삭제하려는 Superuser의 사용자 이름을 여기에 정확히 입력하세요!
username_to_delete = '삭제할_관리자_이름' # 예: 'admin' 또는 'myuser'

try:
    user_to_delete = User.objects.get(username=username_to_delete)
    user_to_delete.delete()
    print(f"사용자 '{username_to_delete}'이(가) 성공적으로 삭제되었습니다.")
except User.DoesNotExist:
    print(f"오류: 사용자 '{username_to_delete}'을(를) 찾을 수 없습니다.")
except Exception as e:
    print(f"오류 발생: {e}")