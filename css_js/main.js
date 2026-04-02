// ボタンの多重クリック対策
document.addEventListener('click', (e) => {
  const btn = e.target.closest('[data-once-click]');
  if (!btn) return;

  if (btn.disabled) {
    e.preventDefault();
    return;
  }

  btn.disabled = true;
});

// =====================
// UILock安全対策まとめ
// =====================

// JSエラー時
window.addEventListener("error", () => {
  setUILock(false);
});

window.addEventListener("unhandledrejection", () => {
  setUILock(false);
});

// 戻る対策（bfcache）
window.addEventListener("pageshow", (event) => {
  if (event.persisted) {
    setUILock(false);
  }
});

// fetchラッパー（任意）
async function safeFetch(url, options = {}) {
  try {
    setUILock(true, "読み込み中...");

    const res = await fetch(url, options);

    if (!res.ok) {
      throw new Error("HTTP " + res.status);
    }

    return await res.json();
  } catch (err) {
    setUILock(false);
    showToast("通信に失敗しました", "error");
    throw err;
  }
}

/************************************/
/* UIロック（ボタン＋オーバーレイ） */
/************************************/
document.addEventListener("submit", function (e) {
  const form = e.target;

  // 例外
  if (form.dataset.noLock === "true") return;

  setUILock(true, "読み込み中...");
});

function setUILock(locked, message = "") {
  const overlay = document.getElementById("overlay");
  const buttons = document.querySelectorAll(
    "button, input[type='button'], input[type='submit']"
  );

  buttons.forEach(btn => btn.disabled = locked);

  overlay.classList.toggle("hidden", !locked);
  document.body.style.cursor = locked ? "not-allowed" : "";

  if (locked) {
    setOverlayMessage(message || "処理中...");
  }
}

function setOverlayMessage(text) {
  const overlay = document.getElementById("overlay");

  let msg = overlay.querySelector(".overlay-text");
  if (!msg) {
    msg = document.createElement("div");
    msg.className = "overlay-text";
    overlay.appendChild(msg);
  }

  msg.textContent = text;
}


/************************************/
/* トースト（中央・キュー制御） */
/************************************/
const toastQueue = [];
let isShowingToast = false;

function showToast(message, type = "info", duration = 2000) {
  toastQueue.push({ message, type, duration });
  processToastQueue();
}

async function processToastQueue() {
  if (isShowingToast || toastQueue.length === 0) return;

  isShowingToast = true;

  const { message, type, duration } = toastQueue.shift();

  const container = document.getElementById("toast-container");

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  await sleep(duration);

  toast.classList.add("fade-out");
  await sleep(200);

  toast.remove();

  isShowingToast = false;
  processToastQueue();
}

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}


/************************************/
/* 確認モーダル */
/************************************/
function showConfirm(message) {
  return new Promise((resolve) => {
    const modal = document.getElementById("confirm-modal");
    const msg = document.getElementById("confirm-message");
    const okBtn = document.getElementById("confirm-ok");
    const cancelBtn = document.getElementById("confirm-cancel");

    msg.textContent = message;
    modal.classList.remove("hidden");

    function cleanup(result) {
      modal.classList.add("hidden");
      okBtn.onclick = null;
      cancelBtn.onclick = null;
      resolve(result);
    }

    okBtn.onclick = () => cleanup(true);
    cancelBtn.onclick = () => cleanup(false);
  });
}


/************************************/
/* API通信（UIは触らない） */
/************************************/
async function apiPost(url, params) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded"
      },
      body: new URLSearchParams(params)
    });

    if (!res.ok) throw new Error();

    const data = await res.json();

    if (data.error) {
      return { ok: false, error: data.error };
    }

    return { ok: true, data };

  } catch {
    return { ok: false, error: "通信エラー" };
  }
}


/************************************/
/* POST遷移 */
/************************************/
function postNavigate(url, params) {


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
}
