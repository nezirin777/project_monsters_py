// main.js

// 全体を即時実行関数(IIFE)で包み、グローバル変数の汚染を防ぐ（カプセル化）
// window.showToast / window.postNavigate / window.safeFetch / window.setUILock だけを公開する
(() => {
    'use strict';

    // ==========================================
    // 状態管理変数
    // ==========================================
    const toastQueue = [];
    let isShowingToast = false;
    let confirmOpen = false;

    // トースト位置設定
    const TOAST_POSITION_KEY = 'toastPosition';

    const TOAST_POSITIONS = [
        'toast-top-center',
        'toast-center',
        'toast-bottom-center',
        'toast-bottom-left',
        'toast-bottom-right'
    ];

    // ==========================================
    // 初期化処理
    // ==========================================
    document.addEventListener("DOMContentLoaded", () => {

        // =========================
        // トースト位置初期化
        // =========================
        loadToastPosition();
        initToastPositionSelector();

        // --- ログイン時のユーザー名自動保存・復元 ---
        // toast-position-select と同様、静的 HTML に存在する要素を対象にしている
        const loginForm = document.getElementById("login_form");

        if (loginForm) {
            const nameInput = loginForm.querySelector('input[name="user_name"]');
            const passInput = loginForm.querySelector('input[name="password"]');

            if (nameInput) {
                const savedName = localStorage.getItem("monsters_saved_username");

                if (savedName) {
                    nameInput.value = savedName;

                    if (passInput) {
                        passInput.focus();
                    }
                }

                loginForm.addEventListener("submit", () => {
                    localStorage.setItem(
                        "monsters_saved_username",
                        nameInput.value
                    );
                });
            }
        }

        // --- 交換所（form_check）用イベントフック ---
        const formCheck = document.getElementById("form_check");

        if (formCheck) {
            formCheck.addEventListener("change", (e) => {
                if (e.target.name === 'm_name') {
                    formCheck.dataset.confirm =
                        `「${e.target.value}」を選択しました。交換を実行しますか？`;
                }
            });
        }

        // --- モンスター画像切り替え ---
        document.querySelectorAll(".monster-select").forEach(select => {

            select.addEventListener("change", () => {
                const form = select.closest("form");
                const targetImgName = select.getAttribute("data-target");
                const img = form.querySelector(`img[name="${targetImgName}"]`);

                if (!img) return;

                const selectedOption = select.options[select.selectedIndex];
                const m_name = selectedOption.getAttribute("data-name") || "0";

                // img.src はブラウザが絶対 URL に変換した値を返すため lastIndexOf で安全にベースパスを切り出せる
                // ※ クエリパラメータが付く場合は URL オブジェクトを使うこと
                const basePath = img.src.substring(0, img.src.lastIndexOf('/'));

                img.onerror = () => {
                    img.src = `${basePath}/0.gif`;
                    img.alt = "画像なし";
                    img.onerror = null;
                };

                img.src = `${basePath}/${m_name}.gif`;
                img.alt = selectedOption.text;
            });
        });
    });

    // ==========================================
    // トースト位置管理
    // ==========================================

    function setToastPosition(position) {
        const container = document.getElementById("toast-container");
        if (!container) return;

        container.classList.remove(...TOAST_POSITIONS);

        const validPosition =
            TOAST_POSITIONS.includes(position)
                ? position
                : 'toast-center';

        container.classList.add(validPosition);

        try {
            localStorage.setItem(TOAST_POSITION_KEY, validPosition);
        } catch {
            // プライベートブラウジング等でストレージが使えない環境では無視する
        }
    }

    function loadToastPosition() {
        let saved = 'toast-center';
        try {
            saved = localStorage.getItem(TOAST_POSITION_KEY) || 'toast-center';
        } catch {
            // ストレージが使えない環境ではデフォルト値を使う
        }

        setToastPosition(saved);

        const select = document.getElementById("toast-position-select");
        if (select) {
            select.value = saved;
        }
    }

    function initToastPositionSelector() {
        const select = document.getElementById("toast-position-select");
        if (!select) return;

        select.addEventListener("change", (e) => {
            setToastPosition(e.target.value);
        });
    }

    // ==========================================
    // フォーム送信制御
    // ==========================================
    document.addEventListener("submit", async (e) => {

        const form = e.target;

        // 並び替えが未保存のまま離脱しようとした場合に確認を挟む。
        // my_page.js の markChanged() が window.partyUnsaved を true にセットする。
        // partyForm 自身の送信は submit リスナー内で false にリセット済みのため二重確認にならない。
        // キャンセル時は handleUILock に到達しないため UIロックは発生しない
        if (window.partyUnsaved) {
            e.preventDefault();
            const ok = await showConfirm("並び替えが未保存です。このまま移動しますか？");
            if (!ok) return;
            window.partyUnsaved = false;
            // 確認 OK 後に改めて送信する。dataset.confirm は空のまま通過させる
            handleUILock(e);
            try {
                form.submit();
            } catch (err) {
                setUILock(false);
                throw err;
            }
            return;
        }

        const confirmMsg = form.dataset.confirm;

        if (!confirmMsg) {
            // 確認不要なフォームはそのまま UIロックだけかけてネイティブ submit に任せる
            handleUILock(e);
            return;
        }

        // 確認が必要なフォームはネイティブ submit を止めてモーダルを出す
        e.preventDefault();

        const ok = await showConfirm(confirmMsg);
        if (!ok) return;

        handleUILock(e);

        // dataset.confirm をクリアしておかないと、
        // submit() が再び submit イベントを発火させたときに二重確認になる
        form.dataset.confirm = "";

        try {
            form.submit();
        } catch (err) {
            // ネイティブ submit が例外を投げた場合（まれだが）ロックを解放する
            setUILock(false);
            throw err;
        }
    });

    // ==========================================
    // UILock
    // ==========================================
    let uiLockTimeout = null;

    function handleUILock(e) {
        const form = e.target;
        if (form.dataset.noLock === "true") return;

        const msg = form.dataset.loading || "処理中...";
        const timeoutSeconds = parseInt(form.dataset.timeout, 10) || 20;

        setUILock(true, msg, timeoutSeconds);
    }

    // setUILock はグローバルに公開する（error_tmp.html 等の外部スクリプトから参照される）
    function setUILock(locked, message = "", timeoutSeconds = 20) {

        const overlay = document.getElementById("overlay");

        // 毎回 querySelectorAll する理由: 動的に追加されたボタンも含めて確実に制御するため
        const buttons = document.querySelectorAll(
            "button, input[type='button'], input[type='submit']"
        );

        if (uiLockTimeout) {
            clearTimeout(uiLockTimeout);
            uiLockTimeout = null;
        }

        if (overlay) {
            overlay.classList.toggle("hidden", !locked);
        }

        buttons.forEach(btn => {
            btn.disabled = locked;
        });

        document.body.style.cursor = locked ? "wait" : "";

        if (locked && overlay) {
            let msgEl = overlay.querySelector(".overlay-text");

            if (!msgEl) {
                msgEl = document.createElement("div");
                msgEl.className = "overlay-text";
                overlay.appendChild(msgEl);
            }

            msgEl.textContent = message;

            uiLockTimeout = setTimeout(() => {
                setUILock(false);

                if (typeof window.showToast === 'function') {
                    window.showToast(
                        "通信がタイムアウトしました。もう一度お試しください。",
                        "error",
                        5000
                    );
                } else {
                    alert("通信がタイムアウトしました。");
                }

            }, timeoutSeconds * 1000);
        }
    }

    // ページ遷移・エラー・bfcache での戻り時にロックを解放する安全網
    window.addEventListener("error", () => { setUILock(false); });
    window.addEventListener("unhandledrejection", () => { setUILock(false); });

    window.addEventListener("pageshow", (event) => {
        // bfcache から復元された場合（ブラウザの「戻る」等）もロックを解放する
        if (event.persisted) {
            setUILock(false);
        }
    });

    window.addEventListener("beforeunload", () => {
        if (uiLockTimeout) {
            clearTimeout(uiLockTimeout);
        }

        // ページ遷移がキャンセルされた（「留まる」を選んだ）場合に UIロックを解放する。
        // beforeunload 後に window が focus を受け取ることで遷移キャンセルを検知する。
        // { once: true } により一度だけ実行されて自動解除される
        window.addEventListener("focus", function releaseOnStay() {
            setUILock(false);
        }, { once: true });
    });

    document.addEventListener("keydown", (e) => {
        const overlay = document.getElementById("overlay");

        if (
            e.key === "Escape"
            && overlay
            && !overlay.classList.contains("hidden")
            && !confirmOpen
        ) {
            setUILock(false);

            if (typeof window.showToast === 'function') {
                window.showToast("処理を中断しました。", "info");
            }
        }
    });

    // ==========================================
    // カスタム確認モーダル
    // ==========================================
    function showConfirm(message) {

        return new Promise((resolve) => {

            if (confirmOpen) {
                // モーダルが開いている間は二重呼び出しを拒否する
                return resolve(false);
            }

            confirmOpen = true;

            const modal    = document.getElementById("confirm-modal");
            const msgEl    = document.getElementById("confirm-message");
            const okBtn    = document.getElementById("confirm-ok");
            const cancelBtn = document.getElementById("confirm-cancel");

            if (!modal || !msgEl || !okBtn || !cancelBtn) {
                console.warn('Confirm modal elements missing.');
                confirmOpen = false;
                return resolve(confirm(message));
            }

            msgEl.textContent = message;
            modal.classList.remove("hidden");
            okBtn.focus();

            function cleanup(result) {
                modal.classList.add("hidden");
                okBtn.onclick = null;
                cancelBtn.onclick = null;
                document.removeEventListener("keydown", onKey);
                confirmOpen = false;
                resolve(result);
            }

            function onKey(e) {
                if (e.key === "Enter")  cleanup(true);
                if (e.key === "Escape") cleanup(false);
            }

            document.addEventListener("keydown", onKey);

            okBtn.onclick     = () => cleanup(true);
            cancelBtn.onclick = () => cleanup(false);

            // モーダル背景クリックでキャンセル
            modal.onclick = (e) => {
                if (e.target === modal) cleanup(false);
            };
        });
    }

    // ==========================================
    // トースト通知
    // ==========================================
    function sleep(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

    // window に公開することで、外部テンプレート（error_tmp.html 等）から呼び出せる
    window.showToast = function(message, type = "info", duration = 3000) {
        toastQueue.push({ message, type, duration });
        processToastQueue();
    };

    async function processToastQueue() {
        if (isShowingToast || toastQueue.length === 0) return;

        isShowingToast = true;

        const { message, type, duration } = toastQueue.shift();

        const container = document.getElementById("toast-container");

        if (!container) {
            console.warn('Toast container missing.');
            isShowingToast = false;
            return;
        }

        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.innerHTML = message;
        container.appendChild(toast);

        await sleep(duration);

        toast.classList.add("fade-out");
        await sleep(200);
        toast.remove();

        isShowingToast = false;
        processToastQueue();
    }

    // ==========================================
    // POST遷移
    // ==========================================
    // window に公開することで、外部テンプレート（error_tmp.html 等）から呼び出せる
    window.postNavigate = function(url, params) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = url;

        for (const key in params) {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = key;
            input.value = params[key];
            form.appendChild(input);
        }

        document.body.appendChild(form);
        form.submit();
    };

    // ==========================================
    // fetchラッパー
    // ==========================================
    window.safeFetch = async function(url, options = {}) {
        try {
            setUILock(true, "読み込み中...");

            const res = await fetch(url, options);

            if (!res.ok) throw new Error("HTTP " + res.status);

            return await res.json();

        } catch (err) {
            setUILock(false);
            window.showToast("通信に失敗しました", "error");
            throw err;
        }
    };

    // window.setUILock を公開することで、外部スクリプト（error_tmp.html 等）から参照できる
    window.setUILock = setUILock;

})();
