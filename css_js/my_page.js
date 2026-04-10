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

// パーティ編成のドラッグ＆ドロップとセレクト変更
document.addEventListener("DOMContentLoaded", () => {

  const partyContainer = document.querySelector(".my_page_pt");

  function getCharaItems() {
    return Array.from(partyContainer.children);
  }

  let dragSrc = null;

  // ======================
  // クラス更新
  // ======================
  function updateCharaClasses() {
    const items = getCharaItems();
    items.forEach((item, index) => {
      for (let i = 1; i <= 10; i++) {
        item.classList.remove(`my_page_chara_${i}`);
      }
      item.classList.add(`my_page_chara_${index + 1}`);
    });
  }

  // ======================
  // 表示用セレクト値更新
  // ======================
  function syncSelectValues() {
    const items = getCharaItems();
    items.forEach((item, index) => {
      const select = item.querySelector("select");
      if (!select) return;

      const newNo = String(index + 1);
      select.name = `c_no${newNo}`;
      select.value = newNo;
      select.dataset.prev = newNo;
    });
  }

  // ======================
  // 保存時に送る正しい値を準備
  // ======================
  function prepareForSubmit() {
    const items = getCharaItems();
    items.forEach((item, index) => {
      const select = item.querySelector("select");
      if (!select) return;

      select.name = `c_no${index + 1}`;
      const originalNo = select.dataset.originalNo || select.value;
      select.value = originalNo;
    });
  }

  // ======================
  // 要素交換
  // ======================
  function swapItems(itemA, itemB) {
    if (itemA === itemB) return;

    const parent = partyContainer;
    const nextA = itemA.nextSibling;
    const nextB = itemB.nextSibling;

    itemA.remove();

    if (nextB) parent.insertBefore(itemA, nextB);
    else parent.appendChild(itemA);

    if (nextA) parent.insertBefore(itemB, nextA);
    else parent.appendChild(itemB);

    updateCharaClasses();
    syncSelectValues();
    markChanged();        // ← ここを確実に呼ぶ
  }

  // ======================
  // ドラッグ＆ドロップ
  // ======================
  function initDragAndDrop() {
    getCharaItems().forEach(item => {
      if (item.dataset.dragInit === "1") return;
      item.dataset.dragInit = "1";
      item.draggable = true;

      item.addEventListener("dragstart", e => {
        dragSrc = item;
        item.classList.add("dragging");
      });

      item.addEventListener("dragend", () => item.classList.remove("dragging"));
      item.addEventListener("dragover", e => e.preventDefault());

      item.addEventListener("drop", e => {
        e.preventDefault();
        if (!dragSrc || dragSrc === item) return;

        swapItems(dragSrc, item);
      });
    });
  }

  // ======================
  // セレクト変更時
  // ======================
  function handleSelectChange(e) {
    const sel = e.target;
    const oldValue = String(sel.dataset.prev || sel.value);
    const newValue = String(sel.value);

    if (oldValue === newValue) return;

    const currentItem = sel.closest('[class^="my_page_chara_"]');
    if (!currentItem) return;

    let targetItem = null;
    getCharaItems().forEach(item => {
      const s = item.querySelector("select");
      if (s && s !== sel && s.value === newValue) {
        targetItem = item;
      }
    });

    if (targetItem) {
      swapItems(currentItem, targetItem);
    }
  }

  // ======================
  // 変更フラグ（ボタンの色変更）
  // ======================
  function markChanged() {
    changed = true;
    const btn = document.querySelector(".my_page_title button");
    if (btn) {
      btn.classList.add("active");
    }
  }

  // ======================
  // 初期化
  // ======================
  function init() {
    initDragAndDrop();

    getCharaItems().forEach(item => {
      const sel = item.querySelector("select");
      if (sel) {
        if (!sel.dataset.changeInit) {
          sel.dataset.changeInit = "1";
          sel.addEventListener("change", handleSelectChange);
        }
        if (!sel.dataset.originalNo) {
          sel.dataset.originalNo = sel.value;
        }
      }
    });

    updateCharaClasses();
    syncSelectValues();
  }

  init();

  // ======================
  // フォーム送信時に送信用値を準備
  // ======================
  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", () => {
      prepareForSubmit();
    });
  }

});
