// --- DOM 요소 변수 선언 ---
// 이 변수들은 script.js 파일 로드 시점에 HTML 요소들이 존재한다고 가정합니다.
// HTML 파일에 해당 ID를 가진 요소들이 있는지 다시 한번 확인해주세요.
const form = document.getElementById('imageGenerationForm');
const loadingSpinner = document.getElementById('loadingSpinner');
const statusMessage = document.getElementById('statusMessage');
const imageResultContainer = document.getElementById('imageResultContainer');
const imageResultsDiv = document.getElementById('imageResults');
const downloadButton = document.getElementById('downloadButton');

// 드래그 앤 드롭 및 파일 미리보기 관련 DOM 요소
const dropArea = document.getElementById('dropArea');
const inputImageFile = document.getElementById('input_image_file'); // <input type="file"> 요소
const selectedImagePreview = document.getElementById('selectedImagePreview'); // 이미지 미리보기 img 태그

let statusCheckInterval; // 이미지 생성 상태를 주기적으로 확인할 setInterval ID를 저장할 변수
let selectedFile = null; // 사용자가 선택하거나 드롭한 파일(File 객체)을 저장할 변수

// --- 드래그 앤 드롭 및 파일 선택 기능 ---

// 1. 드래그 영역을 클릭했을 때 숨겨진 파일 선택 대화상자를 엽니다.
dropArea.addEventListener('click', () => {
    inputImageFile.click(); // 'input_image_file' 엘리먼트(type="file")를 프로그래밍 방식으로 클릭합니다.
});

// 2. 파일 입력 필드의 값이 변경될 때 (파일이 선택되었을 때) 실행됩니다.
inputImageFile.addEventListener('change', (e) => {
    const files = e.target.files; // 선택된 파일들의 FileList 객체를 가져옵니다.
    if (files.length > 0) {
        selectedFile = files[0]; // 첫 번째 파일만 선택하여 selectedFile 변수에 저장합니다.
        handleFilePreview(selectedFile); // 선택된 파일의 미리보기를 표시하는 함수를 호출합니다.
    } else {
        // 파일 선택이 취소되었을 경우, 미리보기를 숨기고 selectedFile을 초기화합니다.
        selectedFile = null;
        selectedImagePreview.style.display = 'none';
        selectedImagePreview.src = '#';
    }
});

// 3. 드래그 오버(dragover) 이벤트: 드래그 중인 아이템이 드롭 영역 위에 있을 때 발생합니다.
//    기본 동작(파일을 새 탭에서 여는 것)을 방지하고, 시각적 피드백(highlight)을 제공합니다.
dropArea.addEventListener('dragover', (e) => {
    e.preventDefault(); // 기본 동작(파일 열기) 방지
    dropArea.classList.add('highlight'); // 드래그 영역에 하이라이트 클래스 추가
});

// 4. 드래그 리브(dragleave) 이벤트: 드래그 중인 아이템이 드롭 영역 밖으로 나갔을 때 발생합니다.
//    하이라이트 클래스를 제거하여 원상 복구합니다.
dropArea.addEventListener('dragleave', () => {
    dropArea.classList.remove('highlight'); // 하이라이트 클래스 제거
});

// 5. 드롭(drop) 이벤트: 드래그 중인 아이템이 드롭 영역에 놓였을 때 발생합니다.
//    기본 동작을 방지하고, 드롭된 파일을 처리합니다.
dropArea.addEventListener('drop', (e) => {
    e.preventDefault(); // 기본 동작 방지
    dropArea.classList.remove('highlight'); // 하이라이트 클래스 제거

    const files = e.dataTransfer.files; // 드롭된 파일들의 FileList 객체를 가져옵니다.
    if (files.length > 0) {
        selectedFile = files[0]; // 첫 번째 드롭된 파일만 selectedFile 변수에 저장합니다.
        handleFilePreview(selectedFile); // 드롭된 파일의 미리보기를 표시합니다.
        // 참고: 브라우저 보안 정책으로 인해 input[type="file"]의 files 속성을 직접 수정하는 것은 어렵습니다.
        // 대신 selectedFile 변수에 저장하고 폼 제출 시 FormData에 직접 추가하는 방식을 사용합니다.
    }
});

// 6. 선택된 파일의 미리보기를 처리하는 헬퍼 함수입니다.
function handleFilePreview(file) {
    if (!file) { // 파일이 없으면 미리보기를 숨깁니다.
        selectedImagePreview.style.display = 'none';
        selectedImagePreview.src = '#';
        return;
    }
    // 파일 타입이 이미지인지 확인합니다.
    if (file.type.startsWith('image/')) {
        const reader = new FileReader(); // FileReader 객체를 생성하여 파일을 읽습니다.
        reader.onload = (e) => {
            selectedImagePreview.src = e.target.result; // 읽은 파일 데이터(Base64 URL)를 이미지 src로 설정
            selectedImagePreview.style.display = 'block'; // 미리보기 이미지를 보이게 합니다.
        };
        reader.readAsDataURL(file); // 파일을 Data URL(Base64) 형식으로 읽습니다.
    } else {
        // 이미지 파일이 아니면 경고 메시지를 표시하고 미리보기를 숨깁니다.
        alert("이미지 파일만 업로드할 수 있습니다.");
        selectedImagePreview.style.display = 'none';
        selectedImagePreview.src = '#';
        selectedFile = null; // 유효하지 않은 파일이므로 selectedFile을 초기화
        inputImageFile.value = ''; // input file 선택을 초기화 (동일 파일 재선택 가능하게)
    }
}


// --- 폼 제출 이벤트 리스너 ---
// 폼이 제출될 때 (사용자가 "이미지 생성" 버튼을 클릭할 때) 실행됩니다.
form.addEventListener('submit', async function(e) {
    e.preventDefault(); // 폼 제출의 기본 동작(페이지 새로고침)을 방지합니다.

    // 이미지 생성 요청 전에 UI 상태를 초기화하고 로딩 상태를 표시합니다.
    statusMessage.textContent = ''; // 이전 상태 메시지 초기화
    imageResultContainer.style.display = 'none'; // 이전 이미지 결과 컨테이너 숨김
    imageResultsDiv.innerHTML = ''; // 이전 생성 이미지들 초기화
    downloadButton.style.display = 'none'; // 다운로드 버튼 숨김

    loadingSpinner.style.display = 'block'; // 로딩 스피너 표시
    statusMessage.textContent = '이미지 생성 요청 중...'; // 상태 메시지 업데이트

    // FormData 객체를 생성하여 폼 데이터를 담습니다.
    // 기존 HTML input 요소의 name 속성을 기반으로 자동으로 데이터를 수집합니다.
    // 드롭된 파일은 별도로 추가해야 합니다.
    const formData = new FormData();
    formData.append('prompt', document.getElementById('prompt').value);
    formData.append('negative_prompt', document.getElementById('negative_prompt').value);
    
    // selectedFile 변수에 저장된 파일이 있다면 'input_image' 이름으로 FormData에 추가합니다.
    if (selectedFile) {
        formData.append('input_image', selectedFile);
    }

    try {
        // Django 백엔드의 이미지 생성 API로 POST 요청을 보냅니다.
        const response = await fetch('/api/generate-image/', {
            method: 'POST',
            body: formData, // FormData 객체를 body로 보냅니다.
        });

        const data = await response.json(); // 서버 응답을 JSON 형식으로 파싱합니다.

        if (response.ok) { // HTTP 상태 코드가 200번대(성공)인 경우
            statusMessage.textContent = data.message; // 서버에서 받은 메시지 표시
            const taskId = data.task_id; // 서버에서 할당받은 작업 ID
            
            // 이전에 설정된 상태 확인 인터벌이 있다면 중지하여 중복 실행을 방지합니다.
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
            }
            // 2초마다 checkStatus 함수를 호출하여 이미지 생성 상태를 확인합니다.
            statusCheckInterval = setInterval(() => checkStatus(taskId), 2000);
        } else { // HTTP 상태 코드가 200번대가 아닌 경우 (예: 400, 500)
            statusMessage.textContent = `오류: ${data.message}`; // 오류 메시지 표시
            loadingSpinner.style.display = 'none'; // 로딩 스피너 숨김
            // 실패 시 모든 결과 관련 UI를 숨깁니다.
            imageResultContainer.style.display = 'none';
            downloadButton.style.display = 'none';
        }
    } catch (error) { // 네트워크 오류 등 예외 발생 시
        console.error('Error:', error); // 콘솔에 오류 로그 출력
        statusMessage.textContent = '이미지 생성 요청 중 네트워크 오류가 발생했습니다.'; // 사용자에게 오류 메시지 표시
        loadingSpinner.style.display = 'none'; // 로딩 스피너 숨김
        // 오류 시 모든 결과 관련 UI를 숨깁니다.
        imageResultContainer.style.display = 'none';
        downloadButton.style.display = 'none';
    }
});

// --- 이미지 생성 상태 확인 함수 ---
// 주기적으로 백엔드 API를 호출하여 이미지 생성 상태를 업데이트합니다.
function checkStatus(taskId) {
    fetch(`/api/task-status/${taskId}/`) // 특정 task_id에 대한 상태를 요청합니다.
        .then(response => response.json()) // 응답을 JSON 형식으로 파싱합니다.
        .then(data => {
            statusMessage.textContent = data.message; // 현재 상태 메시지 업데이트

            if (data.status === "SUCCESS") { // 이미지가 성공적으로 생성된 경우
                clearInterval(statusCheckInterval); // 상태 확인 폴링(interval)을 중지합니다.
                loadingSpinner.style.display = 'none'; // 로딩 스피너 숨김
                imageResultContainer.style.display = 'block'; // 이미지 결과 컨테이너를 보이게 합니다.

                if (data.images && data.images.length > 0) { // 생성된 이미지가 있다면
                    imageResultsDiv.innerHTML = ''; // 기존 이미지들을 지웁니다. (이전에 여러 이미지를 표시할 때를 대비)
                    data.images.forEach(image => { // 각 이미지 정보에 대해 반복합니다.
                        const imgElement = document.createElement('img'); // <img> 태그 생성
                        imgElement.src = image.url; // 이미지 URL 설정
                        imgElement.alt = image.name; // 이미지 대체 텍스트 설정
                        imageResultsDiv.appendChild(imgElement); // 이미지 결과 영역에 추가

                        // 다운로드 버튼 활성화 및 클릭 이벤트 설정
                        // 여기서는 첫 번째 이미지(또는 마지막 루프의 이미지)를 다운로드 대상으로 설정합니다.
                        // 여러 이미지를 각각 다운로드하려면 각 이미지 옆에 다운로드 버튼을 두거나,
                        // 모든 이미지를 압축하여 다운로드하는 로직을 추가해야 합니다.
                        downloadButton.style.display = 'block'; // 다운로드 버튼을 보이게 합니다.
                        downloadButton.onclick = () => { // 버튼 클릭 시 다운로드 로직
                            const a = document.createElement('a'); // 가상의 <a> 태그 생성
                            a.href = image.url; // 다운로드할 이미지 URL
                            a.download = image.name; // 다운로드될 파일명
                            document.body.appendChild(a); // <a> 태그를 body에 임시로 추가 (일부 브라우저에서 필요)
                            a.click(); // <a> 태그 클릭 이벤트를 트리거하여 다운로드 시작
                            document.body.removeChild(a); // 다운로드 후 <a> 태그 제거
                        };
                    });
                }
                statusMessage.textContent = data.message; // 최종 완료 메시지 ("이미지 생성이 완료되었습니다! (이미지 출력)")
            } else if (data.status === "FAILED") { // 이미지 생성에 실패한 경우
                clearInterval(statusCheckInterval); // 폴링 중지
                loadingSpinner.style.display = 'none'; // 로딩 스피너 숨김
                // 실패 시 모든 결과 관련 UI를 숨깁니다.
                imageResultContainer.style.display = 'none';
                downloadButton.style.display = 'none';

                console.error("Image generation failed:", data.message, data.details); // 콘솔에 상세 오류 로그 출력
                statusMessage.textContent = `이미지 생성 실패: ${data.message}`; // 사용자에게 실패 메시지 표시
            } else { // 이미지가 아직 생성 중인 경우
                // 진행 중 메시지와 진행률을 업데이트합니다.
                statusMessage.textContent = `${data.message} (${data.progress}%)`;
            }
        })
        .catch(error => { // API 호출 중 네트워크 오류 발생 시
            console.error('Error checking status:', error); // 콘솔에 오류 로그 출력
            clearInterval(statusCheckInterval); // 폴링 중지
            loadingSpinner.style.display = 'none'; // 로딩 스피너 숨김
            statusMessage.textContent = '상태 확인 중 오류 발생.'; // 사용자에게 오류 메시지 표시
            // 오류 시 모든 결과 관련 UI를 숨깁니다.
            imageResultContainer.style.display = 'none';
            downloadButton.style.display = 'none';
        });
}