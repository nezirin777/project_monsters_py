function countdownTimer() {
    // b_count要素を取得
    const bCount = document.getElementById('b_count');

    // b_countが存在しない場合は早期リターン
    if (!bCount) return;

    // 現在の時刻を取得（秒単位）
    const now = Math.floor(Date.now() / 1000);

    // 戦闘可能時間を取得（秒単位）
    const end = parseInt(document.getElementById('b_count_txt').textContent, 10);

    // 残り時間を計算
    const diff = end - now;

    const battleSubmit = $(".battle_go :submit");

    if (diff <= 0) {
        bCount.textContent = '戦闘OK';
        battleSubmit.prop("disabled", false).css("background-color", "").css("color", "");
    } else {
        bCount.textContent = `次の戦闘まで ${diff} 秒`;
        battleSubmit.prop("disabled", true).css("background-color", "gray").css("color", "darkgray");
        setTimeout(countdownTimer, 1000); // 1秒後に再実行
    }
}

$(document).ready(function () {
    countdownTimer();
});
