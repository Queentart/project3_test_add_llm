# D:\project3_django\test_celery_task.py

import os
import django
import sys
import time

# Django 환경 설정
# Django 프로젝트의 settings.py 파일을 찾을 수 있도록 경로를 설정합니다.
# 이 스크립트를 프로젝트 루트(manage.py가 있는 곳)에 두었다면 아래 경로는 올바릅니다.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# 이제 Django 앱과 Celery 태스크를 임포트할 수 있습니다.
from image_generator.tasks import debug_add
from celery.result import AsyncResult # 태스크 결과를 가져오기 위해 필요

def run_debug_add_test():
    print("--- Celery debug_add 태스크 테스트 시작 ---")

    try:
        print("debug_add 함수를 임포트 중...")
        # from image_generator.tasks import debug_add # 이미 위에서 임포트함
        print("debug_add 함수를 성공적으로 임포트했습니다.")

        print("Celery 태스크를 큐에 추가 중...")
        # 태스크를 Celery 큐에 보냅니다.
        # .delay()는 태스크 객체를 반환하며, 이는 AsyncResult 객체입니다.
        result_async = debug_add.delay(100, 200)

        print(f"태스크가 성공적으로 큐에 추가되었습니다.")
        print(f"  태스크 ID: {result_async.id}")
        print(f"  초기 태스크 상태: {result_async.status}")

        print("\n워커가 태스크를 처리하도록 잠시 기다립니다 (최대 15초)...")
        # 태스크가 완료되기를 기다립니다. (기본 15초 타임아웃)
        # 이 시점에서 Celery 워커 터미널을 확인하세요.
        # ValueError가 여기서 발생할 가능성이 높습니다.
        try:
            # get() 메서드는 태스크가 완료될 때까지 기다리며, 결과를 반환하거나 예외를 발생시킵니다.
            final_result = result_async.get(timeout=15)
            print(f"최종 태스크 상태: {result_async.status}")
            print(f"최종 태스크 결과: {final_result}")

            if result_async.status == 'SUCCESS' and final_result == 300:
                print(">>> 테스트 성공: debug_add 태스크가 정상적으로 처리되었습니다. <<<")
            else:
                print(">>> 테스트 실패: 태스크가 성공 상태가 아니거나 결과가 올바르지 않습니다. <<<")

        except TimeoutError:
            print(f"!!! 테스트 실패: 태스크가 {result_async.status} 상태로 15초 내에 완료되지 않았습니다. 워커를 확인하세요. !!!")
            # 태스크가 타임아웃된 경우, 현재 상태와 가능한 예외 정보를 가져옵니다.
            current_status = AsyncResult(result_async.id)
            print(f"  타임아웃 시점의 태스크 상태: {current_status.status}")
            if current_status.status == 'FAILURE':
                print(f"  실패 원인 (traceback): {current_status.traceback}")
            
        except Exception as e:
            print(f"!!! 테스트 실패: 태스크 실행 중 예외 발생: {e} !!!")
            # 예외 발생 시, 태스크의 현재 상태 및 traceback을 확인합니다.
            current_status = AsyncResult(result_async.id)
            print(f"  예외 발생 시점의 태스크 상태: {current_status.status}")
            if current_status.status == 'FAILURE':
                print(f"  실패 원인 (traceback): {current_status.traceback}")


    except ImportError as e:
        print(f"!!! 임포트 에러 발생: {e} !!!")
        print("  tasks.py 파일의 경로와 이름, 그리고 'debug_add' 함수가 정확히 존재하는지 확인하세요.")
        print("  또한, Celery 워커와 Django 서버를 재시작하고 __pycache__를 삭제했는지 확인하세요.")
    except Exception as e:
        print(f"!!! 예상치 못한 오류 발생: {e} !!!")
        print("  이전 로그를 확인하여 다른 잠재적인 문제점을 찾아보세요.")

    print("\n--- Celery debug_add 태스크 테스트 종료 ---")

if __name__ == "__main__":
    run_debug_add_test()