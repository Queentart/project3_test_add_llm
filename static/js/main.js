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

    // [추가 부분] 대화 기록 관련 요소 참조
    const newChatButton = document.getElementById('new-chat-button');
    const conversationList = document.getElementById('conversation-list');
    const loadMoreConversationsButton = document.getElementById('load-more-conversations');

    let currentConversationId = 'new-chat'; // 현재 대화 ID (초기값 'new-chat')
    let selectedImageFile = null; // 업로드할 이미지 파일
    let currentMode = 'curator'; // 현재 챗봇 모드: 'curator' (도슨트) 또는 'image_generation' (이미지 생성)
    
    // [수정 부분] 대화 기록 관리 변수: 전역 offset과 로드된 대화 수
    let globalOffset = 0; // 현재 로드된 대화의 시작 offset
    let conversationsLoadedCount = 0; // 현재 UI에 표시된 대화 기록 수
    let totalConversationsAvailable = 0; // 백엔드에 존재하는 총 대화 수

    const CONVERSATION_DISPLAY_LIMIT = 5; // 화면에 초기 표시할 최대 대화 기록 수
    const CONVERSATION_LOAD_STEP = 5; // "더 보기" 클릭 시 추가로 로드할 대화 수
    const CONVERSATION_DELETE_THRESHOLD = 10; // 자동 삭제를 시작할 대화 기록 총 수
    let isShowingAllConversations = false; // [추가 부분] 모든 대화를 표시 중인지 여부


    // [수정 사항] 초기 로드 시 모드 설정 및 UI 업데이트 함수
    function updateModeUI(mode) {
        currentMode = mode;
        if (currentMode === 'image_generation') {
            // [수정 부분] 이미지 생성 모드일 때 플레이스홀더 텍스트 변경 (간단한 안내)
            userInput.placeholder = '이미지 생성 프롬프트를 입력하세요 (예: 푸른 하늘을 나는 용)';
            displayNotification("이미지 생성 모드가 활성화되었습니다.");
        } else { // 'curator' 모드
            userInput.placeholder = '메시지를 입력하거나 이미지 분석 프롬프트를 입력하세요...';
            removeImageButton.click(); // 모드 변경 시 이미지 미리보기 초기화
            displayNotification("AI 도슨트 모드가 활성화되었습니다.");
        }
        console.log("Current mode:", currentMode);
        userInput.focus(); // 모드 변경 후 입력 필드에 포커스 설정
    }

    // 초기 로드 시 체크박스 상태에 따라 모드 설정
    updateModeUI(modeToggleButton.checked ? 'image_generation' : 'curator');


    // 2. 메시지 표시 함수
    // [수정됨] 'text' 인자가 undefined 또는 null일 경우를 대비하여 안전하게 문자열로 변환
    function displayMessage(sender, text, imageUrl = null) {
        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message-bubble', sender);

        const messageContent = document.createElement('div');
        messageContent.classList.add('message-content');
        messageContent.textContent = String(text || '');

        if (imageUrl) {
            const imgElement = document.createElement('img');
            imgElement.src = imageUrl;
            imgElement.alt = "생성된 이미지";
            imgElement.classList.add('image-message');
            
            // [추가] 이미지가 있는 버블에 클래스 추가
            messageBubble.classList.add('has-image');

            imgElement.onerror = function() {
                console.error("Failed to load image:", imageUrl);
                this.style.display = 'none'; // 이미지를 숨기거나 대체 텍스트 표시
                const errorText = document.createElement('p');
                errorText.textContent = "이미지를 불러올 수 없습니다.";
                messageContent.appendChild(errorText); // 오류 메시지를 텍스트 콘텐츠에 추가
                // 에러 발생 시 텍스트만 표시되도록 재배치
                messageBubble.innerHTML = ''; // 기존 내용 지우기
                messageBubble.appendChild(messageContent);
                chatHistory.scrollTop = chatHistory.scrollHeight;
            };

            const placeElements = () => {
                const chatHistoryHeight = chatHistory.clientHeight;
                const imageHeight = imgElement.naturalHeight;
                const threshold = chatHistoryHeight * 0.6; // 챗 창 높이의 60%

                // 기존 내용을 지우고 순서에 맞게 다시 추가
                messageBubble.innerHTML = ''; 

                if (imageHeight > threshold) {
                    // 이미지가 클 경우 (60% 초과), 이미지 아래에 메시지 콘텐츠 추가
                    messageBubble.appendChild(imgElement);
                    messageBubble.appendChild(messageContent);
                } else {
                    // 이미지가 작거나 보통일 경우 (60% 이하), 메시지 콘텐츠 위에 이미지 추가
                    messageBubble.appendChild(messageContent);
                    messageBubble.appendChild(imgElement);
                }
                chatHistory.scrollTop = chatHistory.scrollHeight; // 스크롤을 항상 최하단으로
            };

            imgElement.onload = placeElements;

            // 이미지가 캐시되어 즉시 로드될 경우를 대비
            if (imgElement.complete && imgElement.naturalHeight !== 0) {
                placeElements();
            } else {
                // 이미지가 아직 로드되지 않은 경우, 일단 이미지와 텍스트를 기본 순서로 추가
                // (이미지-텍스트 순서로 기본 배치하여 큰 이미지에 대한 요구사항 충족)
                messageBubble.appendChild(imgElement);
                messageBubble.appendChild(messageContent);
            }

        } else {
            // 이미지가 없는 경우, 메시지 콘텐츠만 추가
            messageBubble.appendChild(messageContent);
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
        const userMessage = userInput.value.trim(); // 사용자 입력 텍스트를 그대로 사용
        if (!userMessage && !selectedImageFile) return; // 텍스트나 이미지가 없으면 전송 안 함

        // 사용자 메시지 표시
        displayMessage('user', userMessage, selectedImageFile ? URL.createObjectURL(selectedImageFile) : null);
        userInput.value = ''; // 입력 필드 초기화
        
        // 이미지 미리보기 초기화
        removeImageButton.click(); // 이미지 제거 함수 호출 (selectedImageFile도 null로 만듦)

        sendButton.disabled = true; // 전송 중 버튼 비활성화
        showLoadingSpinner(); // 로딩 스피너 표시

        // [중요 수정 부분 시작] JSON 데이터 객체 구성
        const dataToSend = {
            user_message: userMessage,
            conversation_id: currentConversationId,
            current_mode: currentMode,
            image_data: null // 이미지가 없을 경우 기본값을 명시적으로 null로 설정
        };

        let imageDataPromise = Promise.resolve(null); // Promise로 래핑하여 비동기 처리

        if (selectedImageFile) {
            imageDataPromise = new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = function(e) {
                    resolve(e.target.result); // Base64 Data URL (data:image/...;base64, 포함)
                };
                reader.onerror = function(error) {
                    console.error("Error reading file:", error);
                    reject(error);
                };
                reader.readAsDataURL(selectedImageFile);
            });
        }

        try {
            dataToSend.image_data = await imageDataPromise; // 이미지 데이터가 준비될 때까지 기다림

            // [비동기 처리] fetch API를 사용하여 백엔드 API 호출
            const response = await fetch('/api/process_request/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json', // JSON 전송을 위한 Content-Type
                    'X-CSRFToken': getCookie('csrftoken'), // Django CSRF 토큰
                },
                body: JSON.stringify(dataToSend) // JSON.stringify를 사용하여 JSON 문자열로 변환
            });

            if (!response.ok) {
                // 서버에서 오류 응답이 JSON 형식이 아닐 수 있으므로 text()로 먼저 시도
                const errorText = await response.text();
                let errorMessage = `HTTP error! status: ${response.status}`;
                try {
                    const errorJson = JSON.parse(errorText);
                    errorMessage = errorJson.message || errorMessage;
                } catch (parseError) {
                    // JSON 파싱 실패 시 원본 텍스트 사용
                    errorMessage = `HTTP error! status: ${response.status}, message: ${errorText}`;
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            console.log("Server response:", data);

            if (data.status === 'processing' && data.task_id) {
                // [추가] 이미지 생성 요청이 접수되었음을 사용자에게 알림
                displayMessage('ai', data.response); // views.py에서 보낸 'response' 메시지 표시
                // 이미지 생성과 같이 장시간이 필요한 작업은 task_id를 받아 폴링
                pollTaskStatus(data.task_id);
                // [수정] 새 대화가 생성된 경우 currentConversationId 업데이트 및 대화 목록 새로고침
                if (currentConversationId === 'new-chat' && data.conversation_id) {
                    currentConversationId = data.conversation_id;
                    globalOffset = 0; // 새 대화 생성 시 offset 초기화
                    await loadConversations(false); // 대화 목록 새로고침 (전체 초기화 후 로드)
                    // 새로 생성된 대화가 목록에 추가된 후 선택되도록 함
                    selectConversation(currentConversationId); 
                }
            } else if (data.status === 'success' && data.response) { // [수정] data.ai_response 대신 data.response 사용
                // 큐레이터 모드처럼 즉시 응답이 오는 경우
                hideLoadingSpinner();
                displayMessage('ai', data.response, data.image_url); // [수정] data.ai_response 대신 data.response 사용
                // [수정] 새 대화가 생성된 경우 currentConversationId 업데이트 및 대화 목록 새로고침
                if (currentConversationId === 'new-chat' && data.conversation_id) {
                    currentConversationId = data.conversation_id;
                    globalOffset = 0; // 새 대화 생성 시 offset 초기화
                    await loadConversations(false); // 대화 목록 새로고침 (전체 초기화 후 로드)
                    // 새로 생성된 대화가 목록에 추가된 후 선택되도록 함
                    selectConversation(currentConversationId); 
                } else {
                    // 기존 대화에 메시지가 추가되었으므로 메시지 목록만 새로고침
                    // (displayMessage에서 이미 표시되었으므로 추가적인 로드는 필요 없음)
                }
                // [추가 부분] 대화 완료 후 대화 목록 새로고침 및 정리
                checkAndCleanConversations();
            } else {
                hideLoadingSpinner();
                displayMessage('ai', '응답을 처리하는 데 문제가 발생했습니다.');
            }

        } catch (error) {
            hideLoadingSpinner(); // 오류 발생 시 로딩 스피너 숨김
            console.error('Error sending message:', error);
            displayMessage('ai', `오류 발생: ${error.message || '메시지를 전송할 수 없습니다.'}`);
        } finally {
            sendButton.disabled = false; // 전송 완료 후 버튼 활성화
            userInput.focus(); // 메시지 전송 후 입력 필드에 포커스 설정
        }
    }
    // [중요 수정 부분 끝]

    // 5. 작업 상태 폴링 함수 (이미지 생성 등 비동기 작업용)
    async function pollTaskStatus(taskId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/tasks/${taskId}/status/`);
                const data = await response.json();
                console.log(`Task ${taskId} status:`, data.status, data.message);

                if (data.status === 'COMPLETED') { // 'SUCCESS' 대신 'COMPLETED' 사용
                    clearInterval(pollInterval);
                    hideLoadingSpinner();
                    displayMessage('ai', data.message, data.image_url);
                    // 대화 ID는 이미 sendMessage에서 업데이트되었으므로 여기서는 메시지 목록만 새로고침
                    if (currentConversationId) {
                        await loadMessages(currentConversationId); // [수정] 완료 후 메시지 목록 새로고침
                    }
                    // [추가 부분] 이미지 생성 완료 후 대화 목록 새로고침 및 정리
                    loadConversations(false); // 전체 초기화 후 로드
                    checkAndCleanConversations();
                    userInput.focus(); // 작업 완료 후 입력 필드에 포커스 설정
                } else if (data.status === 'FAILED') { // 'FAILURE' 대신 'FAILED' 사용
                    clearInterval(pollInterval);
                    hideLoadingSpinner();
                    displayMessage('ai', `작업 실패: ${data.message}`);
                    // 실패 메시지는 이미 표시되었으므로 메시지 목록 새로고침은 생략
                    userInput.focus(); // 작업 실패 후 입력 필드에 포커스 설정
                } else {
                    // PENDING 또는 PROCESSING 상태, 계속 폴링
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

    // [추가 부분 시작] 대화 기록 관리 함수들

    // 대화 기록을 로드하고 UI에 표시하는 함수
    async function loadConversations(isAppending = false) { // isAppending 인자 추가
        try {
            // API 호출을 위한 offset 설정
            const currentApiOffset = isAppending ? globalOffset : 0;

            console.log("loadConversations called with offset:", currentApiOffset, "limit:", CONVERSATION_DISPLAY_LIMIT);
            const response = await fetch(`/api/conversations/?offset=${currentApiOffset}&limit=${CONVERSATION_DISPLAY_LIMIT}`);
            if (!response.ok) {
                throw new Error('대화 기록을 불러오는 데 실패했습니다.');
            }
            const data = await response.json();
            totalConversationsAvailable = data.total_count; // 백엔드에서 총 대화 수 업데이트
            console.log("Backend response - conversations:", data.conversations.length, "total_count:", totalConversationsAvailable);

            // [수정 부분] 기존 대화 목록 아이템만 제거하고 버튼은 유지
            // isAppending이 false일 때만 목록을 초기화 (첫 로드 또는 간략히 보기)
            if (!isAppending) {
                const existingItems = conversationList.querySelectorAll('li.conversation-item');
                existingItems.forEach(item => item.remove());
                conversationsLoadedCount = 0; // 로드된 대화 수 초기화
            }
            
            // 가져온 대화 기록을 UI에 추가
            data.conversations.forEach(conv => {
                const listItem = document.createElement('li');
                listItem.classList.add('conversation-item');
                listItem.dataset.conversationId = conv.session_id; // session_id를 data 속성으로 저장

                // 현재 활성화된 대화 표시
                if (conv.session_id === currentConversationId) {
                    listItem.classList.add('active');
                }

                const titleSpan = document.createElement('span');
                titleSpan.classList.add('conversation-title');
                // [수정됨] summary 필드를 우선 사용하고, 없으면 first_message_text 사용
                titleSpan.textContent = conv.title || '새 대화'; // views.py에서 'title'로 전달된 summary 사용
                listItem.appendChild(titleSpan);

                const dateSpan = document.createElement('span');
                dateSpan.classList.add('conversation-date');
                // 날짜 포맷 변경 (예: 2023.05.29)
                const date = new Date(conv.created_at);
                dateSpan.textContent = date.toLocaleDateString('ko-KR', { year: 'numeric', month: '2-digit', day: '2-digit' }).replace(/\. /g, '.').replace(/\.$/, '');
                listItem.appendChild(dateSpan);

                listItem.addEventListener('click', () => selectConversation(conv.session_id));
                // [수정 부분] 버튼 바로 위에 추가
                // loadMoreConversationsButton이 ul의 마지막 자식이라고 가정
                if (loadMoreConversationsButton.parentNode === conversationList) {
                    conversationList.insertBefore(listItem, loadMoreConversationsButton);
                } else {
                    conversationList.appendChild(listItem);
                }
                conversationsLoadedCount++; // UI에 표시된 대화 수 증가
            });

            // 다음 "더 보기" 호출을 위한 globalOffset 업데이트
            globalOffset = currentApiOffset + data.conversations.length;

            // "더 보기" 버튼 표시 여부 결정 및 텍스트/아이콘 변경
            if (conversationsLoadedCount < totalConversationsAvailable) {
                // 아직 모든 대화가 로드되지 않음 -> "더 보기"
                loadMoreConversationsButton.style.display = 'block';
                loadMoreConversationsButton.innerHTML = '더 보기 <i class="bi bi-arrow-down-circle-fill"></i>';
                isShowingAllConversations = false;
            } else {
                // 모든 대화가 로드됨 -> "간략히 보기" 또는 숨김
                if (totalConversationsAvailable > CONVERSATION_DISPLAY_LIMIT) { // 초기 로드 개수보다 많을 때만 "간략히 보기" 표시
                    loadMoreConversationsButton.style.display = 'block';
                    loadMoreConversationsButton.innerHTML = '간략히 보기 <i class="bi bi-arrow-up-circle-fill"></i>';
                    isShowingAllConversations = true;
                } else {
                    // 총 대화 수가 초기 표시 개수보다 적거나 같으면 버튼 숨김
                    loadMoreConversationsButton.style.display = 'none';
                    isShowingAllConversations = false;
                }
            }

            // [수정] 첫 로드 시 (isAppending이 false이고 currentConversationId가 'new-chat'이 아닐 때)
            // 첫 번째 대화 선택 로직. 'new-chat' 상태에서는 자동 선택하지 않음.
            if ((!currentConversationId || currentConversationId === 'new-chat') && data.conversations.length > 0 && !isAppending) {
                // 페이지 초기 로드 시 (currentConversationId가 'new-chat'이 아닐 때)만 첫 대화 선택
                // 또는, 'new-chat' 상태이지만 기존 대화가 하나도 없을 때 (이 경우는 사실상 발생하지 않음)
                if (currentConversationId !== 'new-chat') {
                    selectConversation(data.conversations[0].session_id);
                }
            }

        } catch (error) {
            console.error('대화 기록 로드 오류:', error);
            displayNotification(`대화 기록 로드 오류: ${error.message}`);
        }
    }

    // [추가 부분] 간략히 보기 기능
    async function showLessConversations() {
        console.log("Showing less conversations...");
        globalOffset = 0; // offset 초기화
        isShowingAllConversations = false; // 모든 대화 표시 상태 초기화
        await loadConversations(false); // 처음부터 다시 로드 (초기 5개만)
        // 버튼 텍스트와 아이콘은 loadConversations 내부에서 다시 설정됨
    }


    // 특정 대화 기록을 선택하여 채팅창에 로드하는 함수
    async function loadMessages(conversationId) { // 함수 이름 변경: selectConversation -> loadMessages
        // [수정] selectConversation에서 이 함수를 호출하도록 변경
        // 이 함수는 단순히 메시지를 로드하고 표시하는 역할만 수행
        chatHistory.innerHTML = ''; // 현재 채팅 기록 비우기
        displayNotification(`대화 "${conversationId.substring(0, 8)}..." 로드 중...`);
        showLoadingSpinner();

        try {
            const response = await fetch(`/api/conversations/${conversationId}/`);
            if (!response.ok) {
                throw new Error('대화 기록을 불러오는 데 실패했습니다.');
            }
            const data = await response.json();
            hideLoadingSpinner();
            
            if (data.status === 'success' && data.history) {
                // 첫 AI 메시지 (환영 메시지) 표시
                displayMessage('ai', '안녕하세요! 무엇을 도와드릴까요?'); 
                data.history.forEach(msg => {
                    // [수정됨] msg.text가 null/undefined일 경우 빈 문자열로 처리
                    displayMessage(msg.sender, msg.text || '', msg.image_url);
                });
                chatHistory.scrollTop = chatHistory.scrollHeight; // 스크롤 최하단으로
            } else {
                displayMessage('ai', '대화 기록을 불러올 수 없습니다.');
            }
        } catch (error) {
            hideLoadingSpinner();
            console.error('대화 기록 로드 오류:', error);
            displayNotification('대화 기록 로드 오류: ' + error.message);
        } finally {
            userInput.focus();
        }
    }

    // [추가] 대화 목록에서 특정 대화를 선택하는 함수 (UI 및 데이터 로드)
    async function selectConversation(conversationId) {
        if (currentConversationId === conversationId) return; // 이미 선택된 대화면 아무것도 안 함

        // 기존 활성화된 아이템 비활성화
        const activeItem = document.querySelector('.conversation-item.active');
        if (activeItem) {
            activeItem.classList.remove('active');
        }

        // 새 아이템 활성화
        const selectedItem = document.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }

        currentConversationId = conversationId;
        await loadMessages(conversationId); // 선택된 대화의 메시지 로드
    }


    // 새로운 채팅을 시작하는 함수
    async function createNewChat() {
        // [수정] 새 채팅 시작 시 UI 초기화 로직 강화
        currentConversationId = 'new-chat'; // 새 대화 ID로 설정
        chatHistory.innerHTML = `
            <div class="message-bubble ai">
                <div class="message-content">안녕하세요! 무엇을 도와드릴까요?</div>
            </div>
        `; // 채팅 기록 초기화
        removeImageButton.click(); // 이미지 미리보기 초기화
        userInput.value = ''; // 입력 필드 초기화
        displayNotification("새로운 대화가 시작되었습니다.");
        
        // [수정] 새 채팅 시작 시 대화 목록의 활성화된 아이템 제거
        const activeItem = document.querySelector('.conversation-item.active');
        if (activeItem) {
            activeItem.classList.remove('active');
        }

        // [주석 처리] 새 채팅 시작 시 항상 초기 상태로 대화 목록 로드 (불필요한 자동 선택 방지)
        // globalOffset = 0; 
        // isShowingAllConversations = false;
        // await loadConversations(false); 
        userInput.focus();
    }

    // 대화 기록 수가 임계값을 초과하면 가장 오래된 대화를 삭제하는 함수
    async function checkAndCleanConversations() {
        console.log("checkAndCleanConversations called.");
        try {
            // [수정됨] /api/conversations/ API를 사용하여 total_count를 가져옵니다.
            const response = await fetch('/api/conversations/?offset=0&limit=1'); // 총 개수만 확인하기 위해 1개만 요청
            if (!response.ok) {
                throw new Error('총 대화 개수를 불러오는 데 실패했습니다.');
            }
            const data = await response.json();
            const totalConversations = data.total_count; // total_count 필드 사용
            console.log(`Current total conversations: ${totalConversations}, Threshold: ${CONVERSATION_DELETE_THRESHOLD}`);

            if (totalConversations > CONVERSATION_DELETE_THRESHOLD) {
                const deleteCount = totalConversations - CONVERSATION_DELETE_THRESHOLD;
                console.log(`총 대화 수 (${totalConversations})가 임계값(${CONVERSATION_DELETE_THRESHOLD}) 초과. 오래된 대화 ${deleteCount}개 삭제 요청.`);
                const deleteResponse = await fetch(`/api/conversations/delete_oldest/`, { // 오래된 대화 삭제 API
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCookie('csrftoken'),
                        'Content-Type': 'application/x-www-form-urlencoded' // count 파라미터 전송을 위해 추가
                    },
                    body: `count=${deleteCount}` // count 파라미터를 body에 추가
                });
                if (!deleteResponse.ok) {
                    const errorData = await deleteResponse.json();
                    throw new Error(errorData.message || '오래된 대화 삭제에 실패했습니다.');
                }
                const deleteResult = await deleteResponse.json();
                console.log(deleteResult.message);
                // [수정] 삭제 후 대화 목록을 새로고침하고, globalOffset을 0으로 재설정
                globalOffset = 0;
                await loadConversations(false); // 삭제 후 대화 목록 새로고침 (전체 초기화 후 로드)
            }
        } catch (error) {
            console.error('대화 정리 중 오류 발생:', error);
        }
    }
    // [추가 부분 끝] 대화 기록 관리 함수들


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
            imageUploadInput.value = ''; // input file 값 초기화
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

    // [추가 부분] 새 채팅 버튼 이벤트 리스너
    newChatButton.addEventListener('click', createNewChat);

    // [수정 부분] "더 보기" 버튼 이벤트 리스너 (로직 분기)
    loadMoreConversationsButton.addEventListener('click', () => {
        if (isShowingAllConversations) {
            // 현재 "간략히 보기" 상태이므로, 간략히 보기 함수 호출
            showLessConversations();
        } else {
            // 현재 "더 보기" 상태이므로, 다음 페이지 로드
            // globalOffset은 loadConversations 내부에서 업데이트되므로 여기서는 단순히 true 전달
            loadConversations(true); // 다음 페이지 로드 (기존 목록에 추가)
        }
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

    // 초기 대화 기록 로드
    loadConversations(false); // 첫 로드 시에는 기존 목록을 지우고 새로 불러옵니다.
    
    // 페이지 로드 시 입력 필드에 자동으로 포커스
    userInput.focus();

    // [추가] 페이지 로드 시 대화 정리 함수 호출
    checkAndCleanConversations();
});
