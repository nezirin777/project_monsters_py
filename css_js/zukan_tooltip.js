document.addEventListener('DOMContentLoaded', () => {
    const tooltip = document.getElementById('shared-tooltip');
    if (!tooltip) return;

    document.querySelectorAll('.zukan_img').forEach(img => {
        const tooltipContent = img.dataset.tooltip;

        // マウス移動でカーソル追跡
        img.addEventListener('mousemove', (e) => {
            if (tooltipContent) {
                tooltip.innerHTML = tooltipContent;
                tooltip.style.display = 'block';
                tooltip.style.left = `${e.clientX + 10}px`; // 右10px
                tooltip.style.top = `${e.clientY + 10}px`;  // 下10px
                img.setAttribute('aria-describedby', 'shared-tooltip');
            }
        });

        // ホバー開始
        img.addEventListener('mouseenter', () => {
            if (tooltipContent) {
                tooltip.innerHTML = tooltipContent;
                tooltip.style.display = 'block';
                img.setAttribute('aria-describedby', 'shared-tooltip');
            }
        });

        // ホバー終了
        img.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
            tooltip.innerHTML = '';
            img.removeAttribute('aria-describedby');
        });

        // タッチ操作（モバイル）
        let touchTimeout;
        img.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            touchTimeout = setTimeout(() => {
                if (tooltipContent) {
                    tooltip.innerHTML = tooltipContent;
                    tooltip.style.display = 'block';
                    tooltip.style.left = `${touch.clientX + 10}px`;
                    tooltip.style.top = `${touch.clientY + 10}px`;
                    img.setAttribute('aria-describedby', 'shared-tooltip');
                }
            }, 300);
        });
        img.addEventListener('touchend', () => {
            clearTimeout(touchTimeout);
            setTimeout(() => {
                tooltip.style.display = 'none';
                tooltip.innerHTML = '';
                img.removeAttribute('aria-describedby');
            }, 1000);
        });
    });

    // 画面外防止
    document.addEventListener('mousemove', (e) => {
        if (tooltip.style.display === 'block') {
            const tooltipRect = tooltip.getBoundingClientRect();
            const maxX = window.innerWidth - tooltipRect.width - 5;
            const maxY = window.innerHeight - tooltipRect.height - 5;
            tooltip.style.left = `${Math.min(e.clientX + 10, maxX)}px`;
            tooltip.style.top = `${Math.min(e.clientY + 10, maxY)}px`;
        }
    });
});
