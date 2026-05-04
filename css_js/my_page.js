// my_page.js

document.addEventListener('DOMContentLoaded', () => {

    // ==========================================
    // 1. ショップの説明ポップアップ機能
    // ==========================================
    const linkMsg = document.getElementById('link_msg');
    if (linkMsg) {
        document.querySelectorAll('.my_page_menu4 span').forEach(span => {
            span.addEventListener('mouseover', () => {
                linkMsg.textContent = span.dataset.msg || '説明がここに。';
            });
            span.addEventListener('mouseout', () => {
                linkMsg.textContent = '説明がここに。';
            });
        });
    }

    // ==========================================
    // 2. メニュー（鍵、特技一覧）の開閉機能
    // ==========================================
    document.querySelectorAll('.toggle-menu').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const showId = link.dataset.show;
            const hideId = link.dataset.hide;
            const showEl = document.getElementById(showId);
            const hideEl = document.getElementById(hideId);

            if (!showEl || !hideEl) {
                console.warn('Toggle elements not found:', showId, hideId);
                return;
            }

            hideEl.style.display = 'none';
            showEl.style.display = showEl.style.display === 'block' ? 'none' : 'block';
        });
    });

    // ==========================================
    // 3. パーティ編成（ドラッグ＆ドロップ ＆ セレクト変更）
    // ==========================================
    const partyContainer = document.querySelector(".my_page_pt");

    // 要素が存在しないページ（またはモンスター0匹）の場合はここで処理を止める（安全装置）
    if (!partyContainer) return;

    let dragSrc = null;
    let changed = false;

    function getCharaItems() {
        return Array.from(partyContainer.children);
    }

    // クラス更新
    function updateCharaClasses() {
        const items = getCharaItems();
        items.forEach((item, index) => {
            // クラスを綺麗にお掃除（古いクラスが残るのを防ぐ）
            item.className = item.className.replace(/my_page_chara_\d+/g, '').trim();
            // 新しい順位のクラスを付与
            item.classList.add(`my_page_chara_${index + 1}`);
        });
    }

    // 表示用セレクト値更新
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

    // 保存時に送る正しい値を準備（送信直前に発火）
    function prepareForSubmit() {
        const items = getCharaItems();
        items.forEach((item, index) => {
            const select = item.querySelector("select");
            if (!select) return;

            select.name = `c_no${index + 1}`;
            // サーバーに送る時は、移動先の番号ではなく「元の要素が持っていた固有ID」を送る
            select.value = select.dataset.originalNo || select.value;
        });
    }

    // 変更フラグ（ボタンの色変更）
    function markChanged() {
        changed = true;
        const btn = document.querySelector(".my_page_title button[type='submit']");
        if (btn) {
            btn.classList.add("active");
            // ボタンのテキストを「変更あり！」などの目立つ文言に変えるのもアリです
        }
    }

    // 要素交換処理のコア
    function swapItems(itemA, itemB) {
        if (itemA === itemB) return;

        const parent = partyContainer;
        const nextA = itemA.nextSibling;
        const nextB = itemB.nextSibling;

        // 一旦外して入れ替える
        itemA.remove();
        if (nextB) parent.insertBefore(itemA, nextB);
        else parent.appendChild(itemA);

        if (nextA) parent.insertBefore(itemB, nextA);
        else parent.appendChild(itemB);

        updateCharaClasses();
        syncSelectValues();
        markChanged();
    }

// ドラッグ＆ドロップの初期化
    function initDragAndDrop() {
        getCharaItems().forEach(item => {
            if (item.dataset.dragInit === "1") return;
            item.dataset.dragInit = "1";
            item.draggable = true;

            item.addEventListener("dragstart", () => {
                dragSrc = item;
                item.classList.add("dragging");
                item.style.opacity = '0.5';

                // ドラッグが始まったらコンテナにクラスを付け、CSSと連動してセレクトボックスを無効化する
                partyContainer.classList.add('is-dragging');
            });

            item.addEventListener("dragend", () => {
                item.classList.remove("dragging");
                item.style.opacity = '1';
                getCharaItems().forEach(i => i.classList.remove("drag-over"));

                // ドラッグが終わったらセレクトボックスの操作を復活させる
                partyContainer.classList.remove('is-dragging');
            });

            item.addEventListener("dragenter", (e) => {
                e.preventDefault();
                if (item !== dragSrc) item.classList.add("drag-over");
            });

            item.addEventListener("dragleave", (e) => {
                // ★改善2: 万が一子要素に判定が吸われた場合でも、それが自分の子要素なら「退出していない」とみなす
                if (item.contains(e.relatedTarget)) return;
                item.classList.remove("drag-over");
            });

            item.addEventListener("dragover", e => {
                e.preventDefault(); // 必須
                // ★改善3: 念のための保険。侵入(enter)でクラスが付き損ねても、滞在(over)し続ければ確実に枠を光らせる
                if (item !== dragSrc && !item.classList.contains("drag-over")) {
                    item.classList.add("drag-over");
                }
            });

            item.addEventListener("drop", e => {
                e.preventDefault();
                item.classList.remove("drag-over");
                if (!dragSrc || dragSrc === item) return;

                swapItems(dragSrc, item);
            });
        });
    }

    // セレクトボックス変更時の連動
    function handleSelectChange(e) {
        const sel = e.target;
        const newValue = String(sel.value);
        const oldValue = String(sel.dataset.prev || sel.value);

        if (oldValue === newValue) return;

        const currentItem = sel.closest('[class^="my_page_chara_"]');
        if (!currentItem) return;

        let targetItem = null;
        getCharaItems().forEach(item => {
            const s = item.querySelector("select");
            // 自分以外で、新しい値と同じ値を持っている要素（入れ替え相手）を探す
            if (s && s !== sel && s.value === newValue) {
                targetItem = item;
            }
        });

        if (targetItem) {
            swapItems(currentItem, targetItem);
        }
    }

    // パーティ機能の総合初期化
    function initPartySystem() {
        initDragAndDrop();

        getCharaItems().forEach(item => {
            const sel = item.querySelector("select");
            if (sel) {
                if (!sel.dataset.changeInit) {
                    sel.dataset.changeInit = "1";
                    sel.addEventListener("change", handleSelectChange);
                }
                // 初回の読み込み時に、要素が本来持っていた番号を記録する
                if (!sel.dataset.originalNo) {
                    sel.dataset.originalNo = sel.value;
                }
            }
        });

        updateCharaClasses();
        syncSelectValues();
    }

    // 初期化実行
    initPartySystem();

    // フォーム送信時のイベント（送信用に値をすり替える）
    // ※ 複数のフォームがある可能性があるため、最も近い親フォームを取得する
    const partyForm = partyContainer.closest("form");
    if (partyForm) {
        partyForm.addEventListener("submit", () => {
            prepareForSubmit();
        });
    }

});
