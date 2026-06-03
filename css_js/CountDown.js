// CountDown.js

// 戦闘ボタンのカウントダウン制御。
// endTime（Unixエポック秒）まで残り秒数を表示し、ボタンを無効化する。
// setInterval でなく setTimeout 再帰を使うのは、diff を毎回現在時刻から
// 再計算することで蓄積ドリフトを防ぐため。

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

    // 3. 元のボタンテキストを事前に保存する
    // カウントダウン中は textContent が上書きされるため、終了時の復元用に保持する。
    // HTML側の data-original-text が設定済みであればそちらを優先する。
    buttons.forEach(btn => {
        if (!btn.dataset.originalText) {
            btn.dataset.originalText = btn.textContent;
        }
    });

    // 実際のカウントダウン処理（毎秒呼ばれる関数）
    function updateTimer() {
        // 現在の時刻（秒単位）
        const now = Date.now() / 1000;
        const diff = Math.ceil(endTime - now);

        // diff <= 0: 通常の終了
        // endTime < now - 3600: サーバー時刻が1時間以上古い場合の安全弁
        //（セッション切れやデータ不整合で極端に過去の値が来た場合にボタンを解放する）
        if (diff <= 0 || endTime < now - 3600) {
            // === カウントダウン終了 ===
            buttons.forEach(btn => {
                btn.textContent = btn.dataset.originalText;
                btn.disabled = false;
                btn.classList.remove('countdown-active');
                btn.style.pointerEvents = 'auto';
            });
            return;
        }

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

    // 初回実行をキックする
    updateTimer();
});
