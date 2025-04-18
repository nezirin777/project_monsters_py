// ボタンの多重クリック対策
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (event) => {
            // 現在のフォームの送信ボタン
            const submitButton = form.querySelector('button[type="submit"], input[type="submit"]');
            if (!submitButton || submitButton.disabled) {
                event.preventDefault();
                return;
            }

            // 全送信ボタンを無効化
            const allSubmitButtons = document.querySelectorAll('button[type="submit"], input[type="submit"]');
            allSubmitButtons.forEach(btn => {
                btn.disabled = true;
                btn.classList.add('submitting'); // 視覚的フィードバック
            });

            // タイムアウト（サーバー応答遅延を考慮）
            setTimeout(() => {
                allSubmitButtons.forEach(btn => {
                    btn.disabled = false;
                    btn.classList.remove('submitting');
                });
            }, 10000); // 5秒（調整可）
        });
    });
});

// 自動移動用 post 関数の最適化
function post(path, params, method = 'post') {
    if (!path || !params || typeof params !== 'object') {
        console.warn('Invalid path or parameters');
        return; // パスまたはパラメータが無効な場合
    }

    const form = document.createElement('form');
    form.method = method;
    form.action = path;

    Object.entries(params).forEach(([key, value]) => {
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = key;
        hiddenField.value = value ?? ''; // null/undefinedを空文字に変換
        form.appendChild(hiddenField);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form); // DOMをクリーンアップ
}
