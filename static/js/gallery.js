// static/js/gallery.js

document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('museum-search-input');
    const searchButton = document.getElementById('museum-search-button');
    const regionSelect = document.getElementById('museum-region-select');
    const typeSelect = document.getElementById('museum-type-select');
    const resetButton = document.getElementById('museum-reset-filters');
    const museumListContainer = document.querySelector('.museum-list-container');

    // [수정 사항] 백엔드에서 전달된 정적 데이터를 저장할 변수
    // gallery.html 템플릿 내에 이 데이터를 JSON 형태로 삽입할 예정입니다.
    let allMuseums = []; 
    // [수정 사항] End

    // [수정 사항] 초기 데이터를 로드하고 필터링하는 함수
    function loadAndFilterMuseums() {
        // HTML에서 hidden input 등으로 JSON 데이터를 가져와 allMuseums에 할당합니다.
        // 이 부분은 gallery.html의 스크립트 블록에서 초기화될 것입니다.
        // 예를 들어: allMuseums = JSON.parse(document.getElementById('museum-data').textContent);
        // 지금은 임시로 더미 데이터를 사용합니다. 실제로는 뷰에서 전달받을 데이터입니다.
        if (allMuseums.length === 0) { // 데이터가 아직 로드되지 않았다면 더미 데이터 사용 (개발용)
            // [주석 처리] 더 이상 쓰이지 않는 더미 데이터 (실제로는 뷰에서 전달)
            // console.warn("allMuseums is empty. Using dummy data for development.");
            // allMuseums = [
            //     {
            //         id: 1,
            //         name: "국립현대미술관 서울관",
            //         address: "서울특별시 종로구 삼청로 30",
            //         phone_number: "02-3701-9500",
            //         operating_hours: "10:00 - 18:00 (월요일 휴관)",
            //         description: "다양한 현대미술 작품을 만날 수 있는 곳입니다.",
            //         website: "https://www.mmca.go.kr",
            //         image_url: "/static/images/default_museum_mmca.jpg", // 더미 이미지
            //         region: "seoul",
            //         type: "art_museum"
            //     },
            //     {
            //         id: 2,
            //         name: "디뮤지엄",
            //         address: "서울특별시 성동구 왕십리로83-21",
            //         phone_number: "02-1670-0062",
            //         operating_hours: "11:00 - 19:00 (월요일 휴관)",
            //         description: "젊고 감각적인 전시가 열리는 미술관입니다.",
            //         website: "https://www.dmuseum.org",
            //         image_url: "/static/images/default_museum_dmuseum.jpg",
            //         region: "seoul",
            //         type: "gallery"
            //     },
            //     {
            //         id: 3,
            //         name: "부산시립미술관",
            //         address: "부산광역시 해운대구 APEC로 58",
            //         phone_number: "051-740-4200",
            //         operating_hours: "10:00 - 18:00 (월요일 휴관)",
            //         description: "부산 지역을 대표하는 공립 미술관입니다.",
            //         website: "http://art.busan.go.kr/",
            //         image_url: "/static/images/default_museum_busan.jpg",
            //         region: "busan",
            //         type: "art_museum"
            //     },
            //     {
            //         id: 4,
            //         name: "서울시립미술관",
            //         address: "서울특별시 중구 덕수궁길 61",
            //         phone_number: "02-2124-8800",
            //         operating_hours: "10:00 - 20:00 (월요일 휴관)",
            //         description: "근대에서 현대까지 다양한 예술을 전시합니다.",
            //         website: "https://sema.seoul.go.kr",
            //         image_url: "/static/images/default_museum_sema.jpg",
            //         region: "seoul",
            //         type: "art_museum"
            //     }
            // ];
            // [주석 처리] End
        }

        const searchTerm = searchInput.value.trim().toLowerCase();
        const selectedRegion = regionSelect.value;
        const selectedType = typeSelect.value;

        const filteredMuseums = allMuseums.filter(museum => {
            const matchesSearch = searchTerm === '' || 
                                  museum.name.toLowerCase().includes(searchTerm) || 
                                  museum.address.toLowerCase().includes(searchTerm) ||
                                  (museum.description && museum.description.toLowerCase().includes(searchTerm));
            const matchesRegion = selectedRegion === '' || museum.region === selectedRegion;
            const matchesType = selectedType === '' || museum.type === selectedType;
            
            return matchesSearch && matchesRegion && matchesType;
        });

        renderMuseumList(filteredMuseums);
    }

    // 전시관/미술관 목록을 렌더링하는 함수 (수정 없음)
    function renderMuseumList(museums) {
        museumListContainer.innerHTML = ''; // 기존 내용 지우기
        if (museums.length === 0) {
            museumListContainer.innerHTML = '<p class="no-results">검색 결과가 없습니다.</p>';
            return;
        }

        museums.forEach(museum => {
            const museumCard = document.createElement('div');
            museumCard.classList.add('museum-card');
            museumCard.dataset.museumId = museum.id; 

            museumCard.innerHTML = `
                <img src="${museum.image_url || '/static/images/default_museum.jpg'}" alt="${museum.name} 이미지">
                <div class="museum-card-info">
                    <h3>${museum.name}</h3>
                    <p class="address"><i class="bi bi-geo-alt-fill"></i> ${museum.address}</p>
                    <p class="hours"><i class="bi bi-clock-fill"></i> ${museum.operating_hours || '정보 없음'}</p>
                    <p class="phone"><i class="bi bi-telephone-fill"></i> ${museum.phone_number || '정보 없음'}</p>
                    <p class="description">${museum.description || '설명 없음'}</p>
                    ${museum.website ? `<p class="website-link"><i class="bi bi-globe"></i> <a href="${museum.website}" target="_blank">웹사이트 방문</a></p>` : ''}
                    <div class="museum-card-buttons">
                        <a href="/museums/${museum.id}/" class="btn-detail">상세보기</a>
                    </div>
                </div>
            `;
            museumListContainer.appendChild(museumCard);
        });
    }

    // 2. 이벤트 리스너 연결 (수정 없음)
    searchButton.addEventListener('click', loadAndFilterMuseums);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            loadAndFilterMuseums();
        }
    });
    regionSelect.addEventListener('change', loadAndFilterMuseums);
    typeSelect.addEventListener('change', loadAndFilterMuseums);
    resetButton.addEventListener('click', function() {
        searchInput.value = '';
        regionSelect.value = '';
        typeSelect.value = '';
        loadAndFilterMuseums(); // 필터 초기화 후 다시 불러오기
    });

    // [추가 사항] 초기 데이터 로드를 위한 함수.
    // 이 함수는 gallery.html 내에서 <script> 태그로 호출될 예정입니다.
    window.initializeGalleryData = function(data) {
        allMuseums = data;
        loadAndFilterMuseums(); // 데이터 로드 후 초기 필터링 및 렌더링
    };
    // [추가 사항] End

    // [주석 처리] 초기 갤러리 로드 (이전 API 방식. 이제 initializeGalleryData가 대신함)
    // fetchMuseums(); 
    // [주석 처리] End
});