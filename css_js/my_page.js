// ショップの説明
document.addEventListener('DOMContentLoaded', () => {
    const linkMsg = document.getElementById('link_msg');
    if (!linkMsg) return;

    document.querySelectorAll('.my_page_menu4 span').forEach(span => {
        span.addEventListener('mouseover', () => {
            linkMsg.textContent = span.dataset.msg || '説明がここに。';
        });
        span.addEventListener('mouseout', () => {
            linkMsg.textContent = '説明がここに。';
        });
    });
});

// メニュー鍵、特技一覧開閉
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.toggle-menu').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const showId = link.dataset.show;
            const hideId = link.dataset.hide;
            const showEl = document.getElementById(showId);
            const hideEl = document.getElementById(hideId);
            if (!showEl || !hideEl) {
                console.warn('One or both elements not found:', showId, hideId);
                return;
            }
            hideEl.style.display = 'none';
            showEl.style.display = showEl.style.display === 'block' ? 'none' : 'block';
        });
    });
});

/************************************/
/* メイン処理（教会ボタン） */
/************************************/
async function doKyoukai(btn) {
  const url = btn.dataset.url;
  const token = btn.dataset.token;

  const ok = await showConfirm("お祈りしますか？");
  if (!ok) return;

  // ロック開始
  setUILock(true, "お祈り中...");

  const result = await apiPost(url, {
    mode: "kyoukai_ok",
    token: token
  });

  if (!result.ok) {
    setUILock(false);
    showToast(result.error, "error");
    return;
  }

  showToast("お祈りが天にとどきました", "success");

  setTimeout(() => {
    setUILock(true, "マイページへ移動中...");
    postNavigate(url, {
      mode: "my_page",
      token: token
    });
  }, 800);
}
