function countdownTimer() {
    const bCount = document.getElementById('b_count');
    const bCountTxt = document.getElementById('b_count_txt');
    const buttons = document.querySelectorAll('.battle_go [type="submit"]');

    // 要素の存在チェック
    if (!bCount || !bCountTxt) {
        console.warn('Required elements not found: b_count or b_count_txt');
        return;
    }

    // 現在の時刻（秒単位）
    const now = Math.floor(Date.now() / 1000);
    // 戦闘可能時刻（フォールバック付き）
    const end = parseInt(bCountTxt.textContent, 10) || 0;
    const diff = end - now;

    if (diff <= 0 || end < now - 3600) { // 過去1時間以上は無効
        bCount.textContent = '戦闘OK';
        buttons.forEach(button => {
            button.disabled = false;
        });
    } else {
        bCount.textContent = `次の戦闘まで ${diff} 秒`;
        buttons.forEach(button => {
            button.disabled = true;
        });
    }

    if (diff > 0) {
        setTimeout(countdownTimer, 1000);
    }
}

// ページロード時に実行
document.addEventListener('DOMContentLoaded', () => {
    countdownTimer();
});
