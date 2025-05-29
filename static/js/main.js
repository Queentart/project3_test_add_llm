// static/js/main.js

document.addEventListener('DOMContentLoaded', function() {
    // 1. HTML 요소 참조 가져오기
    const chatHistory = document.getElementById('chat-history');
    const userInput = document.getElementById('user-input');
    const sendButton = document.getElementById('send-button');
    const imageUploadInput = document.getElementById('image-upload-input');
    const imagePreviewArea = document.getElementById('image-preview-area');
    const uploadedImageThumbnail = document.getElementById('uploaded-image-thumbnail');
    const uploadedImageName = document.getElementById('uploaded-image-name');
    const removeImageButton = document.getElementById('remove-image-button');
    const modeToggleButton = document.getElementById('mode-toggle-button'); // 이제 input[type="checkbox"]를 가리킵니다.

    let currentConversationId = 'new-chat'; // 현재 대화 ID (초기값 'new-chat')
    let selectedImageFile = null; // 업로드할 이미지 파일
    let currentMode = 'curator'; // 현재 챗봇 모드: 'curator' (도슨트) 또는 'image_generation' (이미지 생성)

    // [수정 사항] 초기 로드 시 모드 설정 및 UI 업데이트 함수
    // 이미지 업로드 버튼은 항상 표시되도록 로직 변경
    function updateModeUI(mode) {
        currentMode = mode;
        if (currentMode === 'image_generation') {
            userInput.placeholder = '이미지 생성 프롬프트를 입력하세요 (예: 푸른 하늘을 나는 용)';
            // document.querySelector('.image-upload-button').style.display = 'flex'; // [제거] 항상 표시
            displayNotification("이미지 생성 모드가 활성화되었습니다.");
        } else { // 'curator' 모드
            userInput.placeholder = '메시지를 입력하거나 이미지 분석 프롬프트를 입력하세요...'; // [수정] 이미지 분석 안내 추가
            // document.querySelector('.image-upload-button').style.display = 'none'; // [제거] 항상 표시
            removeImageButton.click(); // 모드 변경 시 이미지 미리보기 초기화
            displayNotification("AI 도슨트 모드가 활성화되었습니다.");
        }
        console.log("Current mode:", currentMode);
        userInput.focus(); // 모드 변경 후 입력 필드에 포커스 설정
    }

    // 초기 로드 시 체크박스 상태에 따라 모드 설정
    // 체크박스가 checked 상태이면 'image_generation' 모드, 아니면 'curator' 모드
    // `modeToggleButton.checked`의 초기 상태를 반영하여 UI를 업데이트합니다.
    updateModeUI(modeToggleButton.checked ? 'image_generation' : 'curator');


    // 2. 메시지 표시 함수
    function displayMessage(sender, text, imageUrl = null) {
        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble', sender);

        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.textContent = text;
        messageBubble.appendChild(messageContent);

        if (imageUrl) {
            const imgElement = document.createElement('img');
            imgElement.src = imageUrl;
            imgElement.alt = "생성된 이미지";
            imgElement.classList.add('image-message');
            messageBubble.appendChild(imgElement);
        }

        chatHistory.appendChild(messageBubble);
        chatHistory.scrollTop = chatHistory.scrollHeight; // 스크롤을 항상 최하단으로
    }

    // 알림 메시지 표시 함수
    function displayNotification(message) {
        const notificationBubble = document.createElement('div');
        notificationBubble.classList.add('message-bubble', 'notification');
        const notificationContent = document.createElement('div');
        notificationContent.classList.add('message-content');
        notificationContent.textContent = message;
        notificationBubble.appendChild(notificationContent);
        chatHistory.appendChild(notificationBubble);
        chatHistory.scrollTop = chatHistory.scrollHeight;

        // 3초 후 알림 메시지 제거
        setTimeout(() => {
            notificationBubble.remove();
        }, 3000);
    }

    // 3. 로딩 스피너 표시/숨김 함수
    function showLoadingSpinner() {
        const loadingBubble = document.createElement('div');
        loadingBubble.classList.add('message-bubble', 'ai', 'loading-spinner');
        loadingBubble.id = 'loading-spinner';
        loadingBubble.innerHTML = `
            <div class="message-content">
                <div class="dot-pulse"></div>
                <div class="dot-pulse"></div>
                <div class="dot-pulse"></div>
            </div>
        `;
        chatHistory.appendChild(loadingBubble);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    function hideLoadingSpinner() {
        const spinner = document.getElementById('loading-spinner');
        if (spinner) {
            spinner.remove();
        }
    }

    // 4. 메시지 전송 및 비동기 처리 함수 (가장 중요!)
    async function sendMessage() {
        const text = userInput.value.trim();
        if (!text && !selectedImageFile) return; // 텍스트나 이미지가 없으면 전송 안 함

        // 사용자 메시지 표시
        displayMessage('user', text, selectedImageFile ? URL.createObjectURL(selectedImageFile) : null);
        userInput.value = ''; // 입력 필드 초기화
        
        // 이미지 미리보기 초기화
        imagePreviewArea.style.display = 'none';
        uploadedImageThumbnail.src = '#';
        uploadedImageName.textContent = '';
        const tempSelectedImageFile = selectedImageFile; // 전송 후 초기화를 위해 임시 저장
        selectedImageFile = null;

        sendButton.disabled = true; // 전송 중 버튼 비활성화
        showLoadingSpinner(); // 로딩 스피너 표시

        const formData = new FormData();
        formData.append('user_input', text);
        formData.append('conversation_id', currentConversationId);
        formData.append('mode', currentMode); // 현재 모드 전송

        if (tempSelectedImageFile) {
            formData.append('image_file', tempSelectedImageFile);
        }

        try {
            // [비동기 처리] fetch API를 사용하여 백엔드 API 호출
            const response = await fetch('/api/process_request/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'), // Django CSRF 토큰
                },
                body: formData // FormData 사용 시 Content-Type은 브라우저가 자동으로 설정
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || '서버 응답 오류');
            }

            const data = await response.json();
            console.log("Server response:", data);

            if (data.status === 'processing' && data.task_id) {
                // 이미지 생성과 같이 장시간이 필요한 작업은 task_id를 받아 폴링
                pollTaskStatus(data.task_id);
            } else if (data.status === 'success' && data.ai_response) {
                // 큐레이터 모드처럼 즉시 응답이 오는 경우
                hideLoadingSpinner();
                displayMessage('ai', data.ai_response);
                currentConversationId = data.conversation_id; // 새 대화 시작 시 ID 업데이트
            } else {
                hideLoadingSpinner();
                displayMessage('ai', '응답을 처리하는 데 문제가 발생했습니다.');
            }

        } catch (error) {
            hideLoadingSpinner();
            console.error('Error sending message:', error);
            displayMessage('ai', `오류 발생: ${error.message || '메시지를 전송할 수 없습니다.'}`);
        } finally {
            sendButton.disabled = false; // 전송 완료 후 버튼 활성화
            userInput.focus(); // 메시지 전송 후 입력 필드에 포커스 설정
        }
    }

    // 5. 작업 상태 폴링 함수 (이미지 생성 등 비동기 작업용)
    async function pollTaskStatus(taskId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/task-status/${taskId}/`);
                const data = await response.json();
                console.log(`Task ${taskId} status:`, data.status, data.message);

                if (data.status === 'SUCCESS') {
                    clearInterval(pollInterval);
                    hideLoadingSpinner();
                    displayMessage('ai', data.message, data.image_url);
                    currentConversationId = data.conversation_id; // 대화 ID 업데이트
                    userInput.focus(); // 작업 완료 후 입력 필드에 포커스 설정
                } else if (data.status === 'FAILURE') {
                    clearInterval(pollInterval);
                    hideLoadingSpinner();
                    displayMessage('ai', `작업 실패: ${data.message}`);
                    userInput.focus(); // 작업 실패 후 입력 필드에 포커스 설정
                } else {
                    // PENDING 또는 PROGRESS 상태, 계속 폴링
                    // 필요하다면 진행률 업데이트 로직 추가 (예: 스피너 옆에 % 표시)
                }
            } catch (error) {
                clearInterval(pollInterval);
                hideLoadingSpinner();
                console.error('Error polling task status:', error);
                displayMessage('ai', `작업 상태 확인 중 오류 발생: ${error.message}`);
                userInput.focus(); // 오류 발생 후 입력 필드에 포커스 설정
            }
        }, 2000); // 2초마다 폴링
    }

    // 6. 이벤트 리스너
    sendButton.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !sendButton.disabled) { // 엔터 키 입력 시 전송
            sendMessage();
        }
    });

    // 이미지 업로드 입력 변경 시 미리보기 업데이트
    imageUploadInput.addEventListener('change', function(event) {
        const file = event.target.files[0];
        if (file) {
            selectedImageFile = file;
            uploadedImageThumbnail.src = URL.createObjectURL(file);
            uploadedImageName.textContent = file.name;
            imagePreviewArea.style.display = 'flex';
        } else {
            selectedImageFile = null;
            imagePreviewArea.style.display = 'none';
            uploadedImageThumbnail.src = '#';
            uploadedImageName.textContent = '';
        }
    });

    // 이미지 미리보기 제거 버튼
    removeImageButton.addEventListener('click', function() {
        selectedImageFile = null;
        imageUploadInput.value = ''; // input file 값 초기화
        imagePreviewArea.style.display = 'none';
        uploadedImageThumbnail.src = '#';
        uploadedImageName.textContent = '';
    });

    // 모드 토글 버튼 이벤트 리스너 (체크박스용)
    modeToggleButton.addEventListener('change', function() { // click 대신 change 이벤트 사용
        updateModeUI(this.checked ? 'image_generation' : 'curator');
    });

    // Django CSRF 토큰을 쿠키에서 가져오는 헬퍼 함수
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // 초기 대화 기록 로드 (선택 사항: 서버에서 기존 대화 불러오기)
    // 이 부분은 `get_conversations_api`와 `get_conversation_history_api`를 사용하여 구현할 수 있습니다.
    // 현재는 'new-chat'으로 시작하도록 설정되어 있습니다.
    
    // 페이지 로드 시 입력 필드에 자동으로 포커스
    userInput.focus();
});
