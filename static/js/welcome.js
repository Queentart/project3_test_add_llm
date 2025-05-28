document.addEventListener('DOMContentLoaded', () => {
    // 섹션별 애니메이션 적용 예시 (스크롤 시 나타나도록)
    const sections = document.querySelectorAll('.features-section, .about-section');

    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1 // 뷰포트의 10%가 보일 때 애니메이션 시작
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.querySelectorAll('.section-title, .feature-item, .about-image-area img, .about-text-area p, .learn-more-button').forEach((element, index) => {
                    // 각 요소에 애니메이션 딜레이를 다르게 적용
                    element.style.setProperty('--animation-delay', `${0.3 + index * 0.15}s`);
                    // 이전에 opacity: 0; transform: ...; 로 설정된 CSS 애니메이션을 시작
                    // CSS에서 animation-fill-mode: forwards; 로 최종 상태 유지
                    element.style.animationPlayState = 'running';
                });
                observer.unobserve(entry.target); // 한 번만 실행되도록 관찰 중지
            }
        });
    }, observerOptions);

    sections.forEach(section => {
        observer.observe(section);
    });

    // 히어로 섹션 텍스트 및 이미지 애니메이션은 CSS에서 이미 적용됨.
    // 필요하다면 여기에 추가적인 동적 효과를 구현할 수 있습니다.
    // 예: 버튼 클릭 시 스크롤 이동
    const callToActionBtn = document.querySelector('.call-to-action-button');
    if (callToActionBtn) {
        callToActionBtn.addEventListener('click', () => {
            document.querySelector('.features-section').scrollIntoView({
                behavior: 'smooth'
            });
        });
    }
});