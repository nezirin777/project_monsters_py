// loadbbs.js

document.addEventListener('DOMContentLoaded', () => {
    // グローバル汚染を防ぐため、変数と関数をすべてこの中に閉じ込める（カプセル化）
    const IS_AJAX = 'true';
    let csrfToken = '';
    let currentFol = ''; // URLから取得したフォルダ名を保持

    // fetchラッパー
    async function postFormData(url, formData) {
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });
        if (!response.ok) throw new Error('リクエスト失敗');
        return await response.json();
    }

    // エラー通知の共通化
    function showError(msg) {
        if (typeof showToast === 'function') showToast(msg, 'error');
        else alert(msg);
    }

    // 更新処理
    async function refreshLog() {
        const formData = new FormData();
        formData.append('mode', 'refresh');
        if (currentFol) formData.append('fol', currentFol);
        formData.append('csrf_token', csrfToken);

        try {
            const data = await postFormData('./bbs.py', formData);
            if (data.error) {
                showError(data.error);
            } else {
                document.querySelector('#log-area').innerHTML = data.log;
                csrfToken = data.csrf_token;
            }
        } catch (error) {
            console.error('ログ更新エラー:', error);
            showError('ログの更新に失敗しました');
        }
    }

    // メインの読み込み処理
    async function loadBbs() {
        const bbsDiv = document.getElementById('bbs');
        if (!bbsDiv) return; // 掲示板が存在しないページでは即終了（安全装置）

        try {
            // URLパラメータの解析
            const url = new URL(window.location.href);
            const mode = url.searchParams.get('mode');
            currentFol = url.searchParams.get('fol') || '';

            const fetchUrl = mode === 'view'
                ? `./bbs.py?mode=view${currentFol ? '&fol=' + encodeURIComponent(currentFol) : ''}`
                : './bbs.py';

            // ★改良1: モードに関わらず「HTMLを取得して入れる」処理を共通化
            const response = await fetch(fetchUrl);
            if (!response.ok) throw new Error('データ読み込み失敗');
            bbsDiv.innerHTML = await response.text();

            // 初期トークンの取得
            const tokenInput = bbsDiv.querySelector('input[name="csrf_token"]');
            if (tokenInput) csrfToken = tokenInput.value;

            // ★改良3: HTMLのonclickに頼らず、JS側から「更新」ボタンを探してイベントを付与
            // (type="button" を持つボタンを更新ボタンとして扱う)
            const refreshButton = bbsDiv.querySelector('button[type="button"]');
            if (refreshButton) {
                refreshButton.addEventListener('click', refreshLog);
            }

            // 投稿フォーム（Postモード）がある場合の処理
            const form = bbsDiv.querySelector('form');
            if (form) {
                form.addEventListener('submit', async (event) => {
                    event.preventDefault();

                    const submitButton = form.querySelector('button[type="submit"]');
                    if (submitButton) submitButton.disabled = true;

                    const formData = new FormData(form);
                    formData.append('ajax', IS_AJAX);

                    try {
                        const data = await postFormData(form.action, formData);

                        if (data.error) {
                            showError(data.error);
                        } else {
                            bbsDiv.querySelector('#log-area').innerHTML = data.log;
                            form.querySelector('input[name="csrf_token"]').value = data.csrf_token;
                            csrfToken = data.csrf_token;
                            form.querySelector('input[name="bbs_txt"]').value = '';
                        }
                    } catch (error) {
                        console.error('投稿エラー:', error);
                        showError('通信エラーが発生しました');
                    } finally {
                        if (submitButton) submitButton.disabled = false;
                    }
                });
            }

        } catch (error) {
            console.error('データ読み込みエラー:', error);
            bbsDiv.innerHTML = '<p style="color:red;">データの読み込みに失敗しました</p>';
        }
    }

    // スクリプト読み込み時に実行
    loadBbs();
});
