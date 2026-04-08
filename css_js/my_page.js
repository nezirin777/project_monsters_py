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
/* 状態管理 */
/************************************/
function markChanged() {
  changed = true;

  const submitBtn = document.querySelector(".my_page_title button");
  if (submitBtn) {
    submitBtn.classList.add("active");
  }
}

/************************************/
/* 初期化（全機能まとめ） */
/************************************/
document.addEventListener("DOMContentLoaded", () => {

  const selects = Array.from(document.querySelectorAll("select[name^='c_no']"));
  const items = document.querySelectorAll('[class^="my_page_chara_"]');

  /***************/
  /* 初期値保存 */
  /***************/
  selects.forEach(sel => {
    sel.dataset.prev = sel.value;
  });

  /************************************/
  /* select変更で自動入れ替え */
  /************************************/
  selects.forEach(sel => {
    sel.addEventListener("change", () => {

      const oldValue = sel.dataset.prev;
      const newValue = sel.value;

      if (oldValue === newValue) return;

      const target = selects.find(s => s !== sel && s.value === newValue);

      if (target) {
        target.value = oldValue;
        target.dataset.prev = oldValue;
      } else {
        normalize(selects);
      }

      sel.dataset.prev = newValue;

      normalize(selects);
      markChanged(); // ★ 変更通知

    });
  });

  /************************************/
  /* ドラッグ＆ドロップ */
  /************************************/
  let dragSrc = null;

  items.forEach((el) => {
    el.draggable = true;

    el.addEventListener("dragstart", (e) => {
      dragSrc = el;
      e.dataTransfer.effectAllowed = "move";
    });

    el.addEventListener("dragover", (e) => {
      e.preventDefault();
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

    // prevも更新
    selA.dataset.prev = selA.value;
    selB.dataset.prev = selB.value;

    normalize(selects);
    markChanged(); // ★ 変更通知
  }

  /************************************/
  /* 整合処理（重複防止） */
  /************************************/
  function normalize(selects) {

    const used = new Set();

    selects.forEach(sel => {
      if (used.has(sel.value)) {
        sel.dataset.duplicate = "1";
      } else {
        used.add(sel.value);
        delete sel.dataset.duplicate;
      }
    });

    const max = selects.length;
    const missing = [];

    for (let i = 1; i <= max; i++) {
      if (!used.has(String(i))) {
        missing.push(String(i));
      }
    }

    let mi = 0;
    selects.forEach(sel => {
      if (sel.dataset.duplicate) {
        sel.value = missing[mi++];
        sel.dataset.prev = sel.value;
        delete sel.dataset.duplicate;
      }
    });
  }

});
