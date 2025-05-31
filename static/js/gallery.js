// static/js/gallery.js

document.addEventListener('DOMContentLoaded', function() {
    const citySelect = document.getElementById('city-select');
    // const museumTypeSelect = document.getElementById('museum-type-select'); // 유형 선택 드롭다운은 HTML에서 제거되었으므로 주석 처리
    const resetFilterBtn = document.getElementById('reset-filter-btn');
    const museumListDiv = document.getElementById('museum-list'); // 목록을 렌더링할 div
    const mapContainer = document.getElementById('map'); // 지도 컨테이너

    // [추가] 모달 관련 요소 참조
    const museumDetailModal = new bootstrap.Modal(document.getElementById('museumDetailModal')); // Bootstrap Modal 객체 생성
    const museumDetailModalLabel = document.getElementById('museumDetailModalLabel'); // 모달 제목
    const museumDetailModalBody = document.getElementById('museumDetailModalBody'); // 모달 본문

    let allMuseums = []; // 모든 전시관 데이터를 저장할 변수
    let map = null; // Leaflet 지도 객체
    let markers = []; // 지도에 표시된 마커 배열

    // 1. 지도 초기화 함수
    function initMap() {
        if (map) { // 이미 지도가 초기화되어 있다면 다시 초기화하지 않음
            map.remove();
        }
        // 기본 중심 좌표 (서울 시청)와 확대 레벨 설정
        map = L.map(mapContainer).setView([37.5665, 126.9780], 12); // 서울 중심

        // OpenStreetMap 타일 레이어 추가 (API 키 불필요)
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a> contributors'
        }).addTo(map);

        console.log("Leaflet Map initialized with OpenStreetMap style."); // 로그 메시지 변경
        console.log("Map container element:", mapContainer); // 지도 컨테이너 요소 확인 로그
    }

    // 2. 마커 표시 함수
    function displayMarker(museum) {
        if (!museum.latitude || !museum.longitude) {
            console.warn("Museum missing latitude or longitude:", museum);
            return;
        }

        // [추가] Leaflet 커스텀 아이콘 정의 (부트스트랩 아이콘 사용)
        const customMuseumIcon = L.divIcon({
            className: 'custom-div-icon', // CSS에서 스타일링할 클래스
            html: '<i class="bi bi-shop"></i>', // 부트스트랩 건물 아이콘
            iconSize: [30, 30], // 아이콘의 예상 크기 (CSS에서 실제 폰트 크기 조정)
            iconAnchor: [15, 30], // 아이콘의 중심점 (하단 중앙)
            popupAnchor: [0, -30] // 팝업이 열릴 위치 조정
        });

        const marker = L.marker([museum.latitude, museum.longitude], { icon: customMuseumIcon })
            .addTo(map)
            .bindPopup(`<b>${museum.name}</b><br>${museum.address}<br>${museum.type || ''}`);

        marker.on('click', function() {
            showMuseumDetailModal(museum);
        });
        markers.push(marker); // 마커 배열에 추가
    }

    // 3. 박물관 목록 렌더링 함수
    function renderMuseums(dataToRender) {
        museumListDiv.innerHTML = ''; // 기존 목록 초기화

        // 기존 마커 모두 제거
        markers.forEach(marker => map.removeLayer(marker));
        markers.length = 0; // 배열 비우기

        if (dataToRender.length === 0) {
            museumListDiv.innerHTML = '<p class="no-results">검색 결과가 없습니다.</p>';
            return;
        }

        dataToRender.forEach(museum => {
            const museumItem = document.createElement('div');
            museumItem.className = 'museum-item';
            museumItem.innerHTML = `
                <h3>${museum.name}</h3>
                <p>${museum.address}</p>
                <p><strong>유형:</strong> ${museum.type || 'N/A'}</p>
                <p><strong>운영시간:</strong> ${museum.operating_hours || '정보 없음'}</p>
                <p><strong>연락처:</strong> ${museum.phone || '정보 없음'}</p>
                <button class="btn-detail" data-museum-id="${museum.id}">상세보기</button>
            `;
            // '상세보기' 버튼 클릭 이벤트 리스너
            museumItem.querySelector('.btn-detail').addEventListener('click', function() {
                showMuseumDetailModal(museum);
            });
            museumListDiv.appendChild(museumItem);

            // 지도 마커 추가
            if (museum.latitude && museum.longitude) {
                displayMarker(museum); // displayMarker 함수 호출
            }
        });
    }

    // 4. 필터 적용 함수
    function applyFilters() {
        const selectedCity = citySelect.value;
        // const selectedType = museumTypeSelect.value; // 유형 선택 드롭다운 제거

        let filteredData = allMuseums;

        if (selectedCity) {
            // [수정] museum.city 필드를 직접 사용하여 필터링
            // views.py에서 city 필드가 표준화된 전체 이름(예: "서울특별시")으로 제공됨
            filteredData = filteredData.filter(museum => museum.city && museum.city === selectedCity);
        }
        // if (selectedType) {
        //     filteredData = filteredData.filter(museum => museum.type && museum.type.toLowerCase() === selectedType.toLowerCase());
        // }
        renderMuseums(filteredData);
    }

    // 5. 모달에 상세 정보 표시 함수
    function showMuseumDetailModal(museum) {
        museumDetailModalLabel.textContent = museum.name; // 모달 제목 설정

        let modalBodyContent = `
            <div class="detail-section">
                <p><strong>주소:</strong> ${museum.address}</p>
                <p><strong>유형:</strong> ${museum.type || '정보 없음'}</p>
                <p><strong>개관일:</strong> ${museum.opening_date || '정보 없음'}</p>
                <p><strong>운영시간:</strong> ${museum.operating_hours || '정보 없음'}</p>
                <p><strong>연락처:</strong> ${museum.phone || '정보 없음'}</p>
            </div>
        `;

        // 웹사이트 정보가 있을 경우 추가
        if (museum.website && museum.website !== '정보 없음' && museum.website !== 'N/A' && museum.website.trim() !== '') {
            // URL이 'http' 또는 'https'로 시작하지 않으면 추가
            let websiteUrl = museum.website;
            if (!websiteUrl.startsWith('http://') && !websiteUrl.startsWith('https://')) {
                websiteUrl = 'http://' + websiteUrl; // 기본적으로 http:// 추가
            }
            modalBodyContent += `
                <div class="detail-section website-link">
                    <p><strong>웹사이트:</strong> <a href="${websiteUrl}" target="_blank">${museum.website}</a></p>
                </div>
            `;
        }

        museumDetailModalBody.innerHTML = modalBodyContent; // 모달 본문 내용 설정
        museumDetailModal.show(); // 모달 표시
    }


    // 6. 이벤트 리스너 연결
    citySelect.addEventListener('change', applyFilters);
    // museumTypeSelect.addEventListener('change', applyFilters); // 유형 선택 드롭다운 제거
    resetFilterBtn.addEventListener('click', function() {
        citySelect.value = '';
        // museumTypeSelect.value = ''; // 유형 선택 드롭다운 제거
        renderMuseums(allMuseums); // 전체 데이터로 초기화
    });

    // 7. 초기 데이터 로드 및 초기화
    const museumDataScript = document.getElementById('museum-data-json');
    if (museumDataScript && museumDataScript.textContent) {
        try {
            allMuseums = JSON.parse(museumDataScript.textContent);
            console.log("Initial museum data loaded from hidden script tag:", allMuseums);
            initMap(); // 지도 먼저 초기화
            renderMuseums(allMuseums); // 초기 필터링 없이 전체 데이터 렌더링 (지도 마커 포함)
        } catch (error) {
            console.error("Error parsing museum data from hidden script tag:", error);
            museumListDiv.innerHTML = '<p class="text-red-500">전시관 데이터를 불러오는 데 실패했습니다.</p>';
        }
    } else {
        console.error("No museum data found in hidden script tag or script tag is empty.");
        museumListDiv.innerHTML = '<p class="text-red-500">전시관 데이터를 불러오는 데 실패했습니다.</p>';
    }
});
