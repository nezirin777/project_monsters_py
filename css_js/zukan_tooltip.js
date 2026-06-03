// zukan_tooltip.js

document.addEventListener('DOMContentLoaded', () => {
    const tooltip = document.getElementById('shared-tooltip');
    if (!tooltip) return;

    // touchHideTimeout は複数の img をまたいで共有する（新しい操作で前のタイマーをリセットするため）
    let touchHideTimeout = null;
    const PADDING = 10;

    function updateTooltipPosition(clientX, clientY) {
        const tooltipRect = tooltip.getBoundingClientRect();
        const maxX = window.innerWidth  - tooltipRect.width  - 5;
        const maxY = window.innerHeight - tooltipRect.height - 5;
        const newX = clientX + PADDING;
        const newY = clientY + PADDING;
        tooltip.style.left = `${Math.min(newX, maxX)}px`;
        tooltip.style.top  = `${Math.min(newY, maxY)}px`;
    }

    // ツールチップの表示・非表示を一元管理する
    function showTooltip(content, x, y, sourceImg) {
        // innerHTML への直接代入を避け、textContent で DOM 構築することで XSS を防ぐ。
        // テンプレート側では || 区切りのプレーンテキストとして渡してもらう
        tooltip.innerHTML = '';
        content.split('||').forEach(recipe => {
            const p = document.createElement('p');
            p.textContent = recipe.trim();
            tooltip.appendChild(p);
        });
        tooltip.style.display = 'block';
        sourceImg.setAttribute('aria-describedby', 'shared-tooltip');
        updateTooltipPosition(x, y);
    }

    function hideTooltip() {
        tooltip.style.display = 'none';
        tooltip.innerHTML = '';
        document.querySelector('[aria-describedby="shared-tooltip"]')
            ?.removeAttribute('aria-describedby');
    }

    document.querySelectorAll('.zukan-card__img').forEach(img => {
        const tooltipContent = img.dataset.tooltip;
        if (!tooltipContent) return;

        // PC（マウス）
        img.addEventListener('mouseenter', (e) => {
            showTooltip(tooltipContent, e.clientX, e.clientY, img);
        });

        img.addEventListener('mousemove', (e) => {
            if (tooltip.style.display === 'block') {
                updateTooltipPosition(e.clientX, e.clientY);
            }
        });

        img.addEventListener('mouseleave', () => {
            hideTooltip();
        });

        // スマホ（タッチ）
        // touchPressTimeout は img ごとに独立したタイムアウト（touchHideTimeout とは別管理）
        let touchPressTimeout = null;

        img.addEventListener('touchstart', (e) => {
            // passive: false を明示して preventDefault を有効にする
            // （長押し判定中のスクロール防止のため）
            e.preventDefault();
            clearTimeout(touchHideTimeout);
            const touch = e.touches[0];

            touchPressTimeout = setTimeout(() => {
                // tooltip のサイズが確定してから位置を計算する
                requestAnimationFrame(() => {
                    showTooltip(tooltipContent, touch.clientX, touch.clientY, img);
                });
            }, 300);
        }, { passive: false });

        const endTouch = () => {
            clearTimeout(touchPressTimeout);
            if (tooltip.style.display === 'block') {
                touchHideTimeout = setTimeout(() => {
                    hideTooltip();
                }, 1000);
            }
        };

        img.addEventListener('touchend', endTouch);
        img.addEventListener('touchcancel', endTouch);
    });
});
