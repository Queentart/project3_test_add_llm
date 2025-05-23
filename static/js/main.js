// script.js

document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('dropArea');
    const fileInput = document.getElementById('fileInput');
    const selectedImagePreview = document.getElementById('selectedImagePreview');
    const imagePreviewWrapper = document.getElementById('imagePreviewWrapper');
    const clearImageButton = document.getElementById('clearImageButton');
    const dropAreaText = document.getElementById('dropAreaText');
    const uploadIcon = document.getElementById('uploadIcon'); // 아이콘 요소 추가

    const promptInput = document.getElementById('promptInput');
    const negativePromptInput = document.getElementById('negativePromptInput');
    const generateButton = document.getElementById('generateButton');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const statusMessage = document.getElementById('statusMessage');
    const imageResultContainer = document.getElementById('imageResultContainer');
    const imageResultsDiv = document.getElementById('imageResults');
    const downloadButton = document.getElementById('downloadButton');

    let statusCheckInterval; // 상태 확인을 위한 인터벌 변수

    // =========================================================
    // 이미지 파일 업로드 및 미리보기 관련 로직
    // =========================================================

    // 파일 입력 필드 변경 감지 (클릭으로 파일 선택 시)
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            displayImagePreview(this.files[0]);
        } else {
            hideImagePreview(); // 파일 선택 취소 시 미리보기 숨김
        }
    });

    // 드롭 영역 클릭 시 파일 입력 필드 클릭 (팝업 열기)
    dropArea.addEventListener('click', function(event) {
        // 이미지 미리보기, X 버튼, 아이콘 클릭 시 파일 선택 팝업이 다시 뜨는 것을 방지
        if (event.target.id === 'selectedImagePreview' || 
            event.target.id === 'clearImageButton' ||
            event.target.id === 'uploadIcon') {
            return;
        }
        fileInput.click();
    });

    // 드래그앤드롭 이벤트 처리
    dropArea.addEventListener('dragover', (event) => {
        event.preventDefault(); // 기본 동작 방지 (새 탭에서 파일 열림 방지)
        dropArea.classList.add('highlight');
        dropAreaText.textContent = '여기에 이미지 드롭';
        uploadIcon.style.display = 'none'; // 드래그 중에는 아이콘 숨김
    });

    dropArea.addEventListener('dragleave', () => {
        dropArea.classList.remove('highlight');
        // 이미지가 이미 표시되어 있으면 텍스트와 아이콘은 계속 숨김 상태 유지
        if (imagePreviewWrapper.style.display !== 'block') {
            dropAreaText.textContent = '이미지를 여기에 드래그하거나 클릭하여 업로드';
            dropAreaText.style.display = 'block'; // 텍스트 보이게
            uploadIcon.style.display = 'block'; // 아이콘 보이게
        } else {
             dropAreaText.textContent = '';
             dropAreaText.style.display = 'none'; // 텍스트 숨김
             uploadIcon.style.display = 'none'; // 아이콘 숨김
        }
    });

    dropArea.addEventListener('drop', (event) => {
        event.preventDefault();
        dropArea.classList.remove('highlight');
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files; // 드롭된 파일을 fileInput에 할당
            displayImagePreview(files[0]);
        } else {
            // 드롭된 파일이 없을 경우 (예: 폴더 드롭 등), 초기 상태로 복원
            hideImagePreview(); // 이 함수는 파일 입력 필드도 초기화합니다.
        }
    });

    // 이미지 미리보기 표시 함수
    function displayImagePreview(file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            selectedImagePreview.src = e.target.result;
            imagePreviewWrapper.style.display = 'block'; // 래퍼를 보이게 함
            dropAreaText.style.display = 'none'; // "드래그하거나 클릭하여 업로드" 텍스트 숨김
            uploadIcon.style.display = 'none'; // 아이콘 숨김
            clearImageButton.style.display = 'block'; // X 버튼 보이게 함
        };
        reader.readAsDataURL(file);
    }

    // 이미지 미리보기 숨김 및 초기화 함수
    function hideImagePreview() {
        selectedImagePreview.src = '#'; // 이미지 소스 초기화
        imagePreviewWrapper.style.display = 'none'; // 래퍼를 숨김
        dropAreaText.style.display = 'block'; // 텍스트 다시 보이게 함
        uploadIcon.style.display = 'block'; // 아이콘 다시 보이게 함
        clearImageButton.style.display = 'none'; // X 버튼 숨김
        fileInput.value = ''; // 파일 입력 필드 값 초기화 (가장 중요!)
    }

    // X 버튼 클릭 이벤트 리스너 추가
    clearImageButton.addEventListener('click', function(event) {
        event.stopPropagation(); // 드롭 영역 클릭 이벤트가 발생하지 않도록 전파 중지
        hideImagePreview();
    });

    // 초기 로드 시 이미지 미리보기와 X 버튼 숨기기 (혹시 모를 초기 상태 불일치 방지)
    hideImagePreview();


    // =========================================================
    // AI 이미지 생성 로직
    // =========================================================

    generateButton.addEventListener('click', function() {
        // 기존 작업이 진행 중이면 중복 요청 방지
        if (loadingSpinner.style.display === 'block') {
            return;
        }

        const prompt = promptInput.value;
        const negativePrompt = negativePromptInput.value;
        const imageFile = fileInput.files[0]; // 업로드된 이미지 파일

        if (!prompt.trim()) {
            alert('긍정 프롬프트를 입력해주세요.');
            return;
        }

        loadingSpinner.style.display = 'block';
        statusMessage.textContent = '이미지 생성 요청 중...';
        generateButton.disabled = true; // 버튼 비활성화
        imageResultContainer.style.display = 'none'; // 결과 컨테이너 숨김
        imageResultsDiv.innerHTML = ''; // 이전 결과 이미지 제거
        downloadButton.style.display = 'none'; // 다운로드 버튼 숨김

        const formData = new FormData();
        formData.append('prompt', prompt);
        formData.append('negative_prompt', negativePrompt);
        if (imageFile) {
            formData.append('input_image', imageFile);
        }

        fetch('/api/generate-image/', {
            method: 'POST',
            body: formData,
            headers: {
                'X-CSRFToken': getCookie('csrftoken') // CSRF 토큰 포함
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'accepted') {
                statusMessage.textContent = data.message;
                // 일정 간격으로 상태 확인
                statusCheckInterval = setInterval(() => checkStatus(data.task_id), 2000); // 2초마다 확인
            } else {
                statusMessage.textContent = `오류: ${data.message}`;
                loadingSpinner.style.display = 'none';
                generateButton.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error:', error);
            statusMessage.textContent = '서버 통신 중 오류가 발생했습니다.';
            loadingSpinner.style.display = 'none';
            generateButton.disabled = false;
        });
    });

    function checkStatus(taskId) {
        fetch(`/api/task-status/${taskId}/`)
            .then(response => response.json())
            .then(data => {
                statusMessage.textContent = data.message + ` (${data.progress}%)`; // 진행률 표시
                
                if (data.status === "SUCCESS") {
                    clearInterval(statusCheckInterval); // 작업 완료 시 폴링 중지
                    loadingSpinner.style.display = 'none'; // 로딩 스피너 숨김
                    generateButton.disabled = false; // 버튼 다시 활성화
                    imageResultContainer.style.display = 'block'; // 결과 컨테이너 표시
                    
                    if (data.images && data.images.length > 0) {
                        imageResultsDiv.innerHTML = ''; // 이전 이미지 지우기
                        data.images.forEach(image => {
                            const imgElement = document.createElement('img');
                            imgElement.src = image.url;
                            imgElement.alt = image.name;
                            imageResultsDiv.appendChild(imgElement);

                            downloadButton.style.display = 'block'; // 다운로드 버튼 표시
                            downloadButton.onclick = () => {
                                // 이미지 다운로드 로직
                                const a = document.createElement('a');
                                a.href = image.url;
                                a.download = image.name; // 다운로드될 파일명
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                            };
                        });
                    } else {
                        statusMessage.textContent = "이미지 생성은 완료되었으나, 결과 이미지를 찾을 수 없습니다.";
                    }
                } else if (data.status === "FAILED" || data.status === "NOT_FOUND") {
                    clearInterval(statusCheckInterval);
                    loadingSpinner.style.display = 'none';
                    generateButton.disabled = false;
                    statusMessage.textContent = `오류: ${data.message}`;
                }
            })
            .catch(error => {
                console.error('Error checking status:', error);
                clearInterval(statusCheckInterval);
                loadingSpinner.style.display = 'none';
                generateButton.disabled = false;
                statusMessage.textContent = '상태 확인 중 오류가 발생했습니다.';
            });
    }

    // CSRF 토큰 가져오기 함수 (Django에서 필요)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.startsWith(name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});