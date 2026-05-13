// zukan_tooltip.js

document.addEventListener('DOMContentLoaded', () => {
    const tooltip = document.getElementById('shared-tooltip');
    if (!tooltip) return;

    let touchHideTimeout = null;
    const PADDING = 10;

    function updateTooltipPosition(clientX, clientY) {
        const tooltipRect = tooltip.getBoundingClientRect();
        const maxX = window.innerWidth - tooltipRect.width - 5;
        const maxY = window.innerHeight - tooltipRect.height - 5;
        let newX = clientX + PADDING;
        let newY = clientY + PADDING;
        tooltip.style.left = `${Math.min(newX, maxX)}px`;
        tooltip.style.top  = `${Math.min(newY, maxY)}px`;
    }

    // クラス名変更: .zukan-img-wrapper → .zukan-card__img
    document.querySelectorAll('.zukan-card__img').forEach(img => {
        const tooltipContent = img.dataset.tooltip;
        if (!tooltipContent) return;

        // PC（マウス）
        img.addEventListener('mouseenter', () => {
            tooltip.innerHTML = tooltipContent;
            tooltip.style.display = 'block';
            img.setAttribute('aria-describedby', 'shared-tooltip');
        });

        img.addEventListener('mousemove', (e) => {
            if (tooltip.style.display === 'block') {
                updateTooltipPosition(e.clientX, e.clientY);
            }
        });

        img.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
            tooltip.innerHTML = '';
            img.removeAttribute('aria-describedby');
        });

        // スマホ（タッチ）
        let touchPressTimeout = null;

        img.addEventListener('touchstart', (e) => {
            e.preventDefault();
            clearTimeout(touchHideTimeout);
            const touch = e.touches[0];

            touchPressTimeout = setTimeout(() => {
                tooltip.innerHTML = tooltipContent;
                tooltip.style.display = 'block';
                img.setAttribute('aria-describedby', 'shared-tooltip');
                requestAnimationFrame(() => {
                    updateTooltipPosition(touch.clientX, touch.clientY);
                });
            }, 300);
        });

        const endTouch = () => {
            clearTimeout(touchPressTimeout);
            if (tooltip.style.display === 'block') {
                touchHideTimeout = setTimeout(() => {
                    tooltip.style.display = 'none';
                    tooltip.innerHTML = '';
                    img.removeAttribute('aria-describedby');
                }, 1000);
            }
        };

        img.addEventListener('touchend', endTouch);
        img.addEventListener('touchcancel', endTouch);
    });
});
