// image_generator/static/js/archive.js (또는 project3_test/static/js/archive.js)

document.addEventListener('DOMContentLoaded', function() {
    // 1. HTML 요소 선택
    const searchInput = document.querySelector('.search-box input[type="text"]');
    const searchButton = document.querySelector('.search-box button');
    const styleSelect = document.querySelector('.filter-options select:nth-of-type(1)');
    const sortSelect = document.querySelector('.filter-options select:nth-of-type(2)');
    const resetButton = document.querySelector('.reset-filters');
    const galleryContainer = document.querySelector('.gallery-container');
    const styleGuideChips = document.querySelector('.style-guide-chips'); // 단일 div 요소

    // API로부터 이미지 데이터를 비동기적으로 가져오는 함수
    async function fetchImages() {
        const searchTerm = searchInput.value.trim();
        const selectedStyle = styleSelect.value;
        const selectedSort = sortSelect.value; // 'latest', 'popular', 'random'

        // 디버깅을 위한 로그 (필터링 값 확인)
        console.log("--- fetchImages called with current UI state ---");
        console.log("Search Term:", searchTerm);
        console.log("Selected Style (from select):", selectedStyle);
        console.log("Sort Order (from select):", selectedSort);

        const queryParams = new URLSearchParams();
        if (searchTerm) queryParams.append('search', searchTerm);
        if (selectedStyle) queryParams.append('style', selectedStyle);
        if (selectedSort) queryParams.append('sort', selectedSort);

        const apiUrl = `/api/images/?${queryParams.toString()}`;
        console.log("Constructed API URL:", apiUrl); // API 호출 URL 로그

        try {
            const response = await fetch(apiUrl);
            console.log("API Response Status:", response.status); // API 응답 상태 코드
            if (!response.ok) {
                // HTTP 오류 상태 (예: 404, 500)
                const errorText = await response.text(); // 오류 메시지 확인
                throw new Error(`HTTP error! Status: ${response.status}, Details: ${errorText}`);
            }
            const data = await response.json();
            console.log("API Response Data:", data); // API 응답 데이터 로그
            // JSON 데이터를 바로 렌더링에 사용
            return data;
        } catch (error) {
            console.error("Error fetching images:", error);
            // 사용자에게 오류 메시지 표시
            galleryContainer.innerHTML = '<p class="error-message">이미지를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.</p>';
            return []; // 빈 배열 반환하여 갤러리가 비어있도록 함
        }
    }

    // 가져온 이미지 데이터를 갤러리에 렌더링하는 함수
    function renderGallery(images) {
        galleryContainer.innerHTML = ''; // 기존 갤러리 내용 비우기

        if (images.length === 0) {
            galleryContainer.innerHTML = '<p class="no-results">표시할 이미지가 없습니다. 검색/필터 조건을 변경하거나, 관리자 페이지에서 이미지를 추가해주세요.</p>';
            return;
        }

        images.forEach(image => {
            const galleryItem = document.createElement('div');
            galleryItem.classList.add('gallery-item', 'animate__animated', 'animate__fadeIn');

            const imageUrl = image.image_file; // API 응답에서 'image_file' 키를 사용합니다.

            // 디버깅: 이미지 URL이 유효한지 확인
            if (!imageUrl) {
                console.warn("Missing image_file URL for image ID:", image.id, image.title);
                // 이미지가 없으면 플레이스홀더를 표시하거나 건너뛰기
                galleryItem.innerHTML = `<div class="placeholder-image">이미지 없음</div><div class="gallery-item-info"><h3>${image.title}</h3><p class="prompt">${image.prompt}</p></div>`;
                galleryContainer.appendChild(galleryItem);
                return; // 다음 이미지로 넘어감
            }

            galleryItem.innerHTML = `
                <img src="${imageUrl}" alt="${image.title}">
                <div class="gallery-item-info">
                    <h3>${image.title}</h3>
                    <p class="prompt">${image.prompt}</p>
                    <div class="metadata">
                        <span><i class="bi bi-eye"></i> ${image.views || 0}</span> <span><i class="bi bi-heart"></i> ${image.likes || 0}</span> </div>
                </div>
            `;
            galleryContainer.appendChild(galleryItem);
        });
    }

    // 갤러리를 업데이트하는 메인 함수
    async function updateGallery() {
        // 로딩 스피너 등을 여기에 추가하여 사용자에게 로딩 중임을 알릴 수 있습니다.
        galleryContainer.innerHTML = '<p class="loading-spinner">이미지를 불러오는 중...</p>';
        const images = await fetchImages();
        renderGallery(images);
    }

    // 이벤트 리스너 연결
    searchButton.addEventListener('click', updateGallery);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            updateGallery();
        }
    });
    styleSelect.addEventListener('change', updateGallery);
    sortSelect.addEventListener('change', updateGallery);
    resetButton.addEventListener('click', function() {
        searchInput.value = '';
        styleSelect.value = ''; // '스타일 선택'으로 초기화
        sortSelect.value = 'latest'; // '최신순'으로 초기화
        updateGallery();
    });

    // 스타일 칩스 클릭 이벤트 리스너
    if (styleGuideChips) {
        styleGuideChips.addEventListener('click', function(event) {
            const clickedChip = event.target.closest('span');
            if (clickedChip) {
                const chipText = clickedChip.textContent.trim().toLowerCase(); // "사이버펑크", "카툰/애니메이션" (소문자)
                let styleKeyword = '';

                // 칩 텍스트 (소문자)와 select option value 매핑
                // 이 case 값들은 archive.html의 span 태그 텍스트를 소문자로 변환한 것과 일치해야 합니다.
                switch (chipText) {
                    case '사이버펑크': styleKeyword = 'cyberpunk'; break;
                    case '판타지': styleKeyword = 'fantasy'; break;
                    case '초현실주의': styleKeyword = 'surreal'; break;
                    case '고전 유화': styleKeyword = 'classic'; break;
                    case '카툰/애니메이션': styleKeyword = 'cartoon'; break; // HTML 텍스트와 정확히 일치
                    case '추상화': styleKeyword = 'abstract'; break;
                    case '동양화': styleKeyword = 'oriental'; break;
                    case '수채화': styleKeyword = 'watercolor'; break;
                    case '실사': styleKeyword = 'photorealistic'; break;
                    case '픽셀 아트': styleKeyword = 'pixelart'; break;
                    case '3d 렌더링': styleKeyword = '3d'; break; // HTML '3D 렌더링'의 소문자 형태
                    default: styleKeyword = ''; break;
                }

                if (styleKeyword) {
                    styleSelect.value = styleKeyword; // 드롭다운 값 변경
                    updateGallery(); // 갤러리 업데이트
                } else {
                    console.warn(`[Style Chip] Unknown or unmapped style chip clicked: "${chipText}". Resetting style filter.`);
                    styleSelect.value = ''; // 매핑되지 않은 칩 클릭 시 필터 초기화
                    updateGallery();
                }
            }
        });
    }

    // 3. 페이지 로드 시 초기 갤러리 로드
    updateGallery();
});