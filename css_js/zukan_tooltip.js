// zukan_tooltip.js

document.addEventListener('DOMContentLoaded', () => {
    const tooltip = document.getElementById('shared-tooltip');
    if (!tooltip) return;

    let touchHideTimeout = null; // スマホ用のツールチップ消去タイマー
    const PADDING = 10; // カーソルからツールチップを離す距離(px)

    // ツールチップの座標を更新（画面外にはみ出さないよう調整）
    function updateTooltipPosition(clientX, clientY) {
        const tooltipRect = tooltip.getBoundingClientRect();

        // 画面の右端・下端の限界座標を計算
        // (スクロールバーの幅も考慮して innerWidth から少し引く)
        const maxX = window.innerWidth - tooltipRect.width - 5;
        const maxY = window.innerHeight - tooltipRect.height - 5;

        // カーソルの位置に PADDING を足し、画面限界を超えたら限界値に合わせる
        let newX = clientX + PADDING;
        let newY = clientY + PADDING;

        tooltip.style.left = `${Math.min(newX, maxX)}px`;
        tooltip.style.top = `${Math.min(newY, maxY)}px`;
    }

    // ★修正：新しいクラス名 ".zukan-img-wrapper" に変更
    // （過去の要素も拾えるよう ".zukan_img" も併記して互換性を持たせています）
    document.querySelectorAll('.zukan-img-wrapper, .zukan_img').forEach(img => {
        const tooltipContent = img.dataset.tooltip;
        if (!tooltipContent) return; // ツールチップの中身がない画像は何もしない

        // ==========================================
        // PC（マウス操作）のイベント
        // ==========================================

        // 1. マウスが乗った時（中身のセットと表示を1回だけ行う）
        img.addEventListener('mouseenter', () => {
            tooltip.innerHTML = tooltipContent;
            tooltip.style.display = 'block';
            img.setAttribute('aria-describedby', 'shared-tooltip');
        });

        // 2. マウスが画像の上を動いている時（座標の更新のみ行う。超軽量）
        img.addEventListener('mousemove', (e) => {
            if (tooltip.style.display === 'block') {
                updateTooltipPosition(e.clientX, e.clientY);
            }
        });

        // 3. マウスが外れた時（非表示にする）
        img.addEventListener('mouseleave', () => {
            tooltip.style.display = 'none';
            tooltip.innerHTML = '';
            img.removeAttribute('aria-describedby');
        });

        // ==========================================
        // スマホ・タブレット（タッチ操作）のイベント
        // ==========================================

        let touchPressTimeout = null;

        // 1. 指が触れた時（長押し判定）
        img.addEventListener('touchstart', (e) => {
            // スクロールなどの誤爆を防ぎつつ、他でセットされた消去タイマーを止める
            e.preventDefault();
            clearTimeout(touchHideTimeout);

            const touch = e.touches[0];

            // 300ミリ秒触り続けたら表示
            touchPressTimeout = setTimeout(() => {
                tooltip.innerHTML = tooltipContent;
                tooltip.style.display = 'block';
                img.setAttribute('aria-describedby', 'shared-tooltip');

                // 初回の描画が終わってからサイズを測って座標更新
                requestAnimationFrame(() => {
                    updateTooltipPosition(touch.clientX, touch.clientY);
                });
            }, 300);
        });

        // 2. 指が離れた、またはキャンセルされた時
        const endTouch = () => {
            // 長押しになる前に指が離れたら表示処理をキャンセル
            clearTimeout(touchPressTimeout);

            // 表示されている場合、1秒後に消す（その間に別を触ったらキャンセルされる）
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
