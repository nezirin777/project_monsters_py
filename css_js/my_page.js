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

/************************************/
/* メイン処理（並び替えボタン） */
/************************************/
async function doChange(btn) {
    const url = btn.dataset.url;
    const token = btn.dataset.token;

    const ok = await showConfirm("並び替えますか？");
    if (!ok) return;

    setUILock(true, "並び替え中...");

    // フォーム外ボタンでも select 値を取得可能
    const data = { mode: "change", token: token };
    const form = document.getElementById("party_form");
    const selects = Array.from(form.querySelectorAll("select[name^='c_no']"));


    // select の値を個別キーに変換
    selects.forEach((sel, idx) => {
        data[`c_no${idx+1}`] = parseInt(sel.value);
    });

    const result = await apiPost(url,data);

    if (!result.ok) {
        setUILock(false);
        showToast(result.error, "error");
        return;
    }

    showToast("並び替えが完了しました", "success");

    setTimeout(() => {
        setUILock(true, "マイページへ移動中...");
        postNavigate(url, {
            mode: "my_page",
            token: token
        });
    }, 800);
}

/* ドラッグ＆ドロップで並び替え */

document.addEventListener("DOMContentLoaded", () => {
  const items = document.querySelectorAll('[class^="my_page_chara_"]');

  let dragSrc = null;

  items.forEach((el, index) => {
    el.draggable = true;
    el.dataset.index = index;

    el.addEventListener("dragstart", (e) => {
      dragSrc = el;
      e.dataTransfer.effectAllowed = "move";
    });

    el.addEventListener("dragover", (e) => {
      e.preventDefault(); // これ必須
    });

    el.addEventListener("drop", (e) => {
      e.preventDefault();
      if (!dragSrc || dragSrc === el) return;

      swapSelectValues(dragSrc, el);
    });
  });

  function swapSelectValues(a, b) {
    const selA = a.querySelector("select");
    const selB = b.querySelector("select");

    if (!selA || !selB) return;

    const tmp = selA.value;
    selA.value = selB.value;
    selB.value = tmp;
  }
});


/************************************/
/* メイン処理（本読み） */
/************************************/
async function doHonYomi(btn) {
  const url = btn.dataset.url;
  const token = btn.dataset.token;

  const ok = await showConfirm("本を読みますか？");
  if (!ok) return;

  // ロック開始
  setUILock(true, "本読み中...");

  const form = document.getElementById("book_shop_form");
  const Mno = form.querySelector("select[name='Mno']").value;
  const Bname = form.querySelector("select[name='Bname']").value;

  const result = await apiPost(url, {
    mode: "book_read",
    token: token,
    Mno : Mno,
    Bname : Bname
  });

  if (!result.ok) {
    setUILock(false);
    showToast(result.error, "error");
    return;
  }

  showToast(result.success, "success");

  setTimeout(() => {
    setUILock(true, "本屋に戻ります...");
    postNavigate(url, {
      mode: "books",
      token: token
    });
  }, 800);
}
