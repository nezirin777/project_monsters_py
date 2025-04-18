// ショップの説明
document.addEventListener('DOMContentLoaded', () => {
    const linkMsg = document.getElementById('link_msg');
    if (!linkMsg) return;

    document.querySelectorAll('.my_page_menu4 span').forEach(span => {
        span.addEventListener('mouseover', () => {
            linkMsg.textContent = span.dataset.msg || '説明がここに。';
        });
        span.addEventListener('mouseout', () => {
            linkMsg.textContent = '説明がここに。';
        });
    });
});

// メニュー鍵、特技一覧開閉
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.toggle-menu').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const showId = link.dataset.show;
            const hideId = link.dataset.hide;
            const showEl = document.getElementById(showId);
            const hideEl = document.getElementById(hideId);
            if (!showEl || !hideEl) {
                console.warn('One or both elements not found:', showId, hideId);
                return;
            }
            hideEl.style.display = 'none';
            showEl.style.display = showEl.style.display === 'block' ? 'none' : 'block';
        });
    });
});
