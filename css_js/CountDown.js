// CountDown.js

document.addEventListener('DOMContentLoaded', () => {
    // 1. ページ読み込み時に「1回だけ」HTML要素を探してキャッシュ（保存）する
    const bCountTxt = document.getElementById('b_count_txt');
    const buttons = document.querySelectorAll('.battle-btn');

    if (!bCountTxt || buttons.length === 0) {
        console.warn('Required elements not found');
        return;
    }

    // 2. 目標時刻も最初に1回だけ取得してパースする
    // Python側からは float で来る可能性があるため parseFloat を使用
    const endTime = parseFloat(bCountTxt.textContent) || 0;

    // 実際のカウントダウン処理（毎秒呼ばれる関数）
    function updateTimer() {
        // 現在の時刻（秒単位）
        const now = Date.now() / 1000;
        let diff = Math.ceil(endTime - now);

        if (diff <= 0 || endTime < now - 3600) {
            // 戦闘OKになった時の処理
            // === カウントダウン終了 ===
            buttons.forEach(btn => {
                const originalText = btn.getAttribute('data-original-text') || btn.textContent;
                btn.textContent = originalText;
                btn.disabled = false;
                btn.classList.remove('countdown-active');
                btn.style.pointerEvents = 'auto';
            });
            return;
        } else {
          // === カウントダウン中 ===
          const countdownText = `次の戦闘まで ${diff}秒`;

          buttons.forEach(btn => {
              btn.textContent = countdownText;
              btn.disabled = true;
              btn.classList.add('countdown-active');
              btn.style.pointerEvents = 'none';
          });

          setTimeout(updateTimer, 1000);
        }
    }

    // 初回実行をキックする
    updateTimer();
});
