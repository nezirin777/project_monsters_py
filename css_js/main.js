// main.js

// 全体を即時実行関数(IIFE)で包み、グローバル変数の汚染を防ぐ（カプセル化）
(() => {
    'use strict'; // より厳格なエラーチェックを有効化

    // ==========================================
    // 状態管理変数（外部からはアクセス不可）
    // ==========================================
    const toastQueue = [];
    let isShowingToast = false;
    let confirmOpen = false;

    // ==========================================
    // 初期化処理（ページ読み込み完了時）
    // ==========================================
    document.addEventListener("DOMContentLoaded", () => {

        // --- ログイン時のユーザー名自動保存・復元（キャッシュ事故防止の安全版） ---
        const loginForm = document.getElementById("login_form");
        if (loginForm) {
            const nameInput = loginForm.querySelector('input[name="user_name"]');
            const passInput = loginForm.querySelector('input[name="password"]');

            if (nameInput) {
                // 1. ページ読み込み時：端末に記憶されている名前があればセットする
                const savedName = localStorage.getItem("monsters_saved_username");
                if (savedName) {
                    nameInput.value = savedName;
                    // 名前が自動入力されたら、カーソルをパスワード欄に自動で合わせる（UX向上！）
                    if (passInput) passInput.focus();
                }

                // 2. ログインボタンを押した時：入力されている名前を端末に記憶する
                loginForm.addEventListener("submit", () => {
                    localStorage.setItem("monsters_saved_username", nameInput.value);
                });
            }
        }

        // --- 交換所（form_check）用イベントフック ---
        const formCheck = document.getElementById("form_check");
        if (formCheck) {
            formCheck.addEventListener("change", (e) => {
                if (e.target.name === 'm_name') {
                    formCheck.dataset.confirm = `「${e.target.value}」を選択しました。交換を実行しますか？`;
                }
            });
        }

        // --- モンスター画像切り替え（img_change）用イベントフック ---
        document.querySelectorAll(".monster-select").forEach(select => {
            select.addEventListener("change", (e) => {
                const form = select.closest("form");
                const targetImgName = select.getAttribute("data-target");
                const img = form.querySelector(`img[name="${targetImgName}"]`);

                if (!img) return;

                const selectedOption = select.options[select.selectedIndex];
                const m_name = selectedOption.getAttribute("data-name") || "0";
                const basePath = img.src.substring(0, img.src.lastIndexOf('/'));

                // 画像読み込みエラー時のフォールバック処理
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
    // フォーム送信制御（UIロック ＆ カスタム確認モーダル）
    // ==========================================
    document.addEventListener("submit", async (e) => {
        const form = e.target;
        const confirmMsg = form.dataset.confirm;

        // 確認メッセージが設定されていなければ、そのままUIロックして送信
        if (!confirmMsg) {
            handleUILock(e);
            return;
        }

        // 一旦送信を止める
        e.preventDefault();

        // モーダルを表示してユーザーの選択を待つ
        const ok = await showConfirm(confirmMsg);
        if (!ok) return;

        // 承諾されたらUIをロック
        handleUILock(e);

        // 無限ループを防ぐためにメッセージを消去して再送信
        form.dataset.confirm = "";
        form.submit();
    });

    // ==========================================
    // UILock（二重送信防止とローディング表示）
    // ==========================================
    let uiLockTimeout = null; // タイムアウト監視用の変数

    function handleUILock(e) {
        const form = e.target;
        if (form.dataset.noLock === "true") return;

        const msg = form.dataset.loading || "処理中...";

        // 処理が重い可能性がある場合、フォーム側で data-timeout="30" のように指定できるようにする
        const timeoutSeconds = parseInt(form.dataset.timeout, 10) || 20;

        setUILock(true, msg, timeoutSeconds);
    }

    function setUILock(locked, message = "", timeoutSeconds = 20) {
        const overlay = document.getElementById("overlay");
        const buttons = document.querySelectorAll(
            "button, input[type='button'], input[type='submit']"
        );

        // タイマーのクリア（ロック解除時、または新しいロックがかかった時）
        if (uiLockTimeout) {
            clearTimeout(uiLockTimeout);
            uiLockTimeout = null;
        }

        if (overlay) {
            overlay.classList.toggle("hidden", !locked);
        }

        buttons.forEach(btn => btn.disabled = locked);
        document.body.style.cursor = locked ? "wait" : ""; // 処理中であることが分かりやすいよう wait に変更

        if (locked && overlay) {
            let msgEl = overlay.querySelector(".overlay-text");
            if (!msgEl) {
                msgEl = document.createElement("div");
                msgEl.className = "overlay-text";
                overlay.appendChild(msgEl);
            }
            msgEl.textContent = message;

            // ★改善1: タイムアウト（強制解除）の設定
            // サーバーダウン等でロックされたままになるのを防ぐ
            uiLockTimeout = setTimeout(() => {
                setUILock(false);
                if (typeof window.showToast === 'function') {
                    window.showToast("通信がタイムアウトしました。もう一度お試しください。", "error", 5000);
                } else {
                    alert("通信がタイムアウトしました。");
                }
            }, timeoutSeconds * 1000);
        }
    }

    //  UILock安全対策の強化（エラー時、通信中断時）
    window.addEventListener("error", () => setUILock(false));
    window.addEventListener("unhandledrejection", () => setUILock(false));
    window.addEventListener("pageshow", (event) => {
        if (event.persisted) setUILock(false); // bfcache（戻るボタン）対策
    });

    // ページ遷移が開始されたらタイムアウトを止める（正常な遷移中にタイムアウトエラーが出るのを防ぐ）
    window.addEventListener("beforeunload", () => {
        if (uiLockTimeout) clearTimeout(uiLockTimeout);
    });

    // Escキーが押されたら強制的にロックを解除する（ユーザーの中止操作への対応）
    document.addEventListener("keydown", (e) => {
        // Escキーが押され、かつモーダルが開いていない場合にのみロックを解除
        const overlay = document.getElementById("overlay");
        if (e.key === "Escape" && overlay && !overlay.classList.contains("hidden") && !confirmOpen) {
            setUILock(false);
            if (typeof window.showToast === 'function') {
                window.showToast("処理を中断しました。", "info");
            }
            // フォームの通信自体を強制切断する場合は window.stop() も有効ですが、
            // POST送信中の場合は予期せぬデータ破損を招くため、今回はUIの解除に留めます。
        }
    });

    // ==========================================
    // カスタム確認モーダル
    // ==========================================
    function showConfirm(message) {
        return new Promise((resolve) => {
            if (confirmOpen) return resolve(false);
            confirmOpen = true;

            const modal = document.getElementById("confirm-modal");
            const msgEl = document.getElementById("confirm-message");
            const okBtn = document.getElementById("confirm-ok");
            const cancelBtn = document.getElementById("confirm-cancel");

            if (!modal || !msgEl || !okBtn || !cancelBtn) {
                console.warn('Confirm modal elements missing. Falling back to native confirm.');
                confirmOpen = false;
                return resolve(confirm(message)); // HTMLが用意されていない場合の保険
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
                if (e.key === "Enter") cleanup(true);
                if (e.key === "Escape") cleanup(false);
            }

            document.addEventListener("keydown", onKey);
            okBtn.onclick = () => cleanup(true);
            cancelBtn.onclick = () => cleanup(false);
            modal.onclick = (e) => { if (e.target === modal) cleanup(false); };
        });
    }

    // ==========================================
    // トースト通知（画面下部へのポップアップ）
    // ==========================================
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 外部からトーストを呼び出せるように、windowオブジェクトに公開する（これだけは例外）
    window.showToast = function(message, type = "info", duration = 4000) {
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
    // POST遷移（のち廃止予定）
    // ==========================================
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

    // fetchラッパー（外部から使えるように公開）
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
        } finally {
            // finally にしておけば、成功してもロック解除などを組み込みやすいです（必要に応じて）
        }
    };

})();
