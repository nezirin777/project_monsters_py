// CountDown.js

document.addEventListener('DOMContentLoaded', () => {
    // 1. ページ読み込み時に「1回だけ」HTML要素を探してキャッシュ（保存）する
    const bCount = document.getElementById('b_count');
    const bCountTxt = document.getElementById('b_count_txt');
    const buttons = document.querySelectorAll('.battle_go [type="submit"]');

    if (!bCount || !bCountTxt) {
        console.warn('Required elements not found: b_count or b_count_txt');
        return;
    }

    // 2. 目標時刻も最初に1回だけ取得してパースする
    // Python側からは float で来る可能性があるため parseFloat を使用
    const end = parseFloat(bCountTxt.textContent) || 0;

    // 実際のカウントダウン処理（毎秒呼ばれる関数）
    function updateTimer() {
        // 現在の時刻（秒単位）
        const now = Date.now() / 1000;

        // Math.ceil() で切り上げることで「0秒」ジャストで切り替わるように調整
        const diff = Math.ceil(end - now);

        if (diff <= 0 || end < now - 3600) {
            // 戦闘OKになった時の処理
            bCount.textContent = '戦闘OK';
            bCount.style.color = '#ff5722'; // UX向上: OKになったら色を変えて目立たせる（お好みで）
            bCount.style.fontWeight = 'bold';

            buttons.forEach(button => {
                button.disabled = false;
            });
        } else {
            // カウントダウン中の処理
            bCount.textContent = `次の戦闘まで ${diff} 秒`;
            bCount.style.color = ''; // 色を元に戻す
            bCount.style.fontWeight = 'normal';

            buttons.forEach(button => {
                button.disabled = true;
            });

            // まだ時間が残っていれば1秒後(1000ms)に再度自分自身を呼び出す
            setTimeout(updateTimer, 1000);
        }
    }

    // 初回実行をキックする
    updateTimer();
});
