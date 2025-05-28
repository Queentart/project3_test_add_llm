import os
from transformers import HfHubCache

def clear_huggingface_cache():
    """
    Hugging Face 모델 캐시를 삭제합니다.
    주의: 이 함수는 모든 다운로드된 모델 파일을 영구적으로 삭제합니다.
    """
    try:
        cache = HfHubCache()
        # 캐시의 루트 경로를 확인하고 사용자에게 알립니다.
        cache_dir = os.path.expanduser(cache.cache_dir)
        print(f"Attempting to clear Hugging Face cache at: {cache_dir}")

        # 모든 캐시된 모델 파일을 삭제합니다.
        cache.delete_all_files() 
        print("Hugging Face cache cleared successfully.")
    except Exception as e:
        print(f"Error clearing Hugging Face cache: {e}")
        print("You might need to manually delete the cache directory if the issue persists.")
        # 캐시 디렉토리가 존재하지 않거나 권한 문제일 수 있습니다.
        # 이 경우 수동 삭제를 안내합니다.
        print(f"Manual cache directory location: {os.path.expanduser('~/.cache/huggingface/hub')}")

if __name__ == "__main__":
    print("--- Starting Hugging Face Cache Clear Utility ---")
    clear_huggingface_cache()
    print("--- Hugging Face Cache Clear Utility Finished ---")
    print("\nNow, please re-run your translation_service.py to re-download the models:")
    print('  python -u "d:\\project3_test\\llm_cores\\translation_service.py"')