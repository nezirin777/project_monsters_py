// bbs.js

const IS_AJAX = 'true';
let csrfToken = '';

async function postFormData(url, formData) {
    const response = await fetch(url, {
        method: 'POST',
        body: formData,
        credentials: 'same-origin'
    });

    if (!response.ok) throw new Error('リクエスト失敗');

    return await response.json();
}

async function refreshLog(fol = '') {
    const formData = new FormData();
    console.log('送信トークン:', csrfToken);
    formData.append('mode', 'refresh');
    if (fol) formData.append('fol', fol);
    formData.append('csrf_token', csrfToken);

    try {
        const data = await postFormData('./bbs.py', formData);

        if (data.error) {
            alert(data.error);
        } else {
            document.querySelector('#log-area').innerHTML = data.log;
            csrfToken = data.csrf_token;
        }
    } catch (error) {
        console.error('ログ更新エラー:', error);
        const logArea = document.querySelector('#log-area');
        if (logArea) {
            logArea.insertAdjacentHTML('beforeend', '<p style="color:red;">ログの更新に失敗しました</p>');
        }
    }
}

async function handleViewMode(fetchUrl, fol) {
    const response = await fetch(fetchUrl);
    if (!response.ok) throw new Error('データ読み込み失敗');

    const data = await response.text();
    const bbsDiv = document.getElementById('bbs');
    bbsDiv.innerHTML = data;

    const refreshButton = bbsDiv.querySelector('button[onclick="refreshLog()"]');
    if (refreshButton) {
        refreshButton.onclick = () => refreshLog(fol);
    }
}

async function handlePostMode(fetchUrl) {
    const response = await fetch(fetchUrl);
    if (!response.ok) throw new Error('データ読み込み失敗');

    const data = await response.text();
    const bbsDiv = document.getElementById('bbs');
    bbsDiv.innerHTML = data;

    const tokenInput = bbsDiv.querySelector('input[name="csrf_token"]');
    if (tokenInput) {
        csrfToken = tokenInput.value;
        console.log('初期CSRFトークン取得:', csrfToken);
    }

    const form = bbsDiv.querySelector('form');
    if (!form) return;

    form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) submitButton.disabled = true;

        const formData = new FormData(form);
        formData.append('ajax', IS_AJAX);

        try {
            const data = await postFormData(form.action, formData);

            if (data.error) {
                alert(data.error);
            } else {
                bbsDiv.querySelector('#log-area').innerHTML = data.log;
                form.querySelector('input[name="csrf_token"]').value = data.csrf_token;
                csrfToken = data.csrf_token; // ← ここで保持
                form.querySelector('input[name="bbs_txt"]').value = '';
            }
        } catch (error) {
            console.error('投稿エラー:', error);
            bbsDiv.insertAdjacentHTML('beforeend', '<p style="color:red;">投稿に失敗しました</p>');
        } finally {
            if (submitButton) submitButton.disabled = false;
        }
    });
}

async function loadBbs() {
    try {
        const url = new URL(window.location.href);
        const mode = url.searchParams.get('mode');
        const fol = url.searchParams.get('fol') || '';
        const fetchUrl = mode === 'view'
            ? `./bbs.py?mode=view${fol ? '&fol=' + encodeURIComponent(fol) : ''}`
            : './bbs.py';

        if (mode === 'view') {
            await handleViewMode(fetchUrl, fol);
        } else {
            await handlePostMode(fetchUrl);
        }
    } catch (error) {
        console.error('データ読み込みエラー:', error);
        const bbsDiv = document.getElementById('bbs');
        if (bbsDiv) {
            bbsDiv.innerHTML = '<p style="color:red;">データの読み込みに失敗しました</p>';
        }
    }
}

window.addEventListener('DOMContentLoaded', loadBbs);
