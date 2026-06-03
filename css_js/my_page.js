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
    document.querySelectorAll('.toggle-trigger').forEach(trigger => {
        trigger.addEventListener('click', (e) => {
            e.preventDefault();

            const targetId = trigger.dataset.target;
            const target = document.getElementById(targetId);

            if (!target) {
                console.warn(`Target not found: #${targetId}`);
                return;
            }

            // style.display で開閉を制御する。
            // CSS の初期値は display:none のため、未設定('')は「閉じている」と判断する
            if (target.style.display === 'block') {
                target.style.display = 'none';
            } else {
                target.style.display = 'block';
            }
        });
    });

    // ==========================================
    // 3. パーティ編成（ドラッグ＆ドロップ ＆ セレクト変更）
    // ==========================================
    const partyContainer = document.getElementById("party-container");

    // 要素が存在しないページ（またはモンスター0匹）の場合はここで処理を止める（安全装置）
    if (!partyContainer) return;

    let dragSrc = null;

    // 未保存の変更があるかどうかのフラグ。
    // true のとき beforeunload で離脱警告を出す
    let changed = false;

    // ==========================================
    // 離脱警告
    // ==========================================

    // 並び替え未保存のまま離脱しようとした場合に確認ダイアログを出す。
    // Chrome 等の主要ブラウザは returnValue の文字列を無視して固定メッセージを表示する。
    // フォーム送信による正常な遷移では changed を false にリセットするためダイアログは出ない
    function handleBeforeUnload(e) {
        if (!changed) return;
        e.preventDefault();
    }

    window.addEventListener("beforeunload", handleBeforeUnload);

    function getCharaItems() {
        return Array.from(partyContainer.children);
    }

    // クラスの更新
    function updateCharaClasses() {
        const items = getCharaItems();
        items.forEach((item, index) => {
            // 古いクラスを除去してから新しい順位のクラスを付与する
            item.className = item.className.replace(/my_page_chara_\d+/g, '').trim();
            item.classList.add(`my_page_chara_${index + 1}`);
        });
    }

    // 表示用セレクト値の更新（送信値ではなく表示順番号を同期する）
    function syncSelectValues() {
        const items = getCharaItems();
        items.forEach((item, index) => {
            const select = item.querySelector("select");
            if (!select) return;

            const newNo = String(index + 1);
            select.name = `c_no${newNo}`;
            select.value = newNo;
            // dataset.prev はここでは更新しない。
            // handleSelectChange が変更前後の値を比較するために使うため、
            // ここで上書きすると変更検知が常にスキップされてしまう
        });
    }

    // 送信直前に「元のモンスター固有番号」を送信値としてセットする
    function prepareForSubmit() {
        const items = getCharaItems();
        items.forEach((item, index) => {
            const select = item.querySelector("select");
            if (!select) return;

            select.name = `c_no${index + 1}`;

            if (!select.dataset.originalNo) {
                // 通常ここには来ない。initPartySystem で必ず設定される
                console.warn(`originalNo が未設定です: index=${index}`);
            }

            // サーバーに送る値は「現在の表示位置番号」ではなく「元の固有番号」
            select.value = select.dataset.originalNo || select.value;
        });
    }

    // 変更フラグとボタンの状態を更新する
    function markChanged() {
        changed = true;
        const btn = document.querySelector(".party-action-footer .btn");
        if (btn) {
            btn.classList.add("active");
            btn.textContent = "並び替えOK (未保存)";
        }
    }

    // 要素の位置を入れ替える
    function swapItems(itemA, itemB) {
        if (itemA === itemB) return;

        // nextSibling を事前に保存することで、隣接する要素の入れ替えも正しく処理できる。
        // nextA === itemB のケース（AとBが隣接）でも DOM 仕様上ノーオペレーションになるため安全
        const nextA = itemA.nextSibling;
        const nextB = itemB.nextSibling;

        itemA.remove();
        if (nextB) partyContainer.insertBefore(itemA, nextB);
        else partyContainer.appendChild(itemA);

        if (nextA) partyContainer.insertBefore(itemB, nextA);
        else partyContainer.appendChild(itemB);

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
                partyContainer.classList.add('is-dragging');

                // ドラッグ中はセレクトボックスをロックして誤操作を防ぐ
                getCharaItems().forEach(i => {
                    const s = i.querySelector("select");
                    if (s) s.style.pointerEvents = "none";
                });
            });

            item.addEventListener("dragend", () => {
                item.classList.remove("dragging");
                item.style.opacity = '1';
                getCharaItems().forEach(i => i.classList.remove("drag-over"));
                partyContainer.classList.remove('is-dragging');

                // ドラッグ完了後にセレクトボックスのロックを解除する
                getCharaItems().forEach(i => {
                    const s = i.querySelector("select");
                    if (s) s.style.pointerEvents = "auto";
                });
            });

            item.addEventListener("dragenter", (e) => {
                e.preventDefault();
                if (item !== dragSrc) item.classList.add("drag-over");
            });

            item.addEventListener("dragleave", (e) => {
                if (item.contains(e.relatedTarget)) return;
                item.classList.remove("drag-over");
            });

            item.addEventListener("dragover", e => {
                // preventDefault しないとドロップが受け付けられない（DOM 仕様）
                e.preventDefault();
                // drag-over クラスの追加は dragenter で行う
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

        const currentItem = sel.closest('.party-card');
        if (!currentItem) return;

        let targetItem = null;
        getCharaItems().forEach(item => {
            const s = item.querySelector("select");
            // 自分以外で新しい値と同じ値を持つ要素（入れ替え相手）を探す
            if (s && s !== sel && s.value === newValue) {
                targetItem = item;
            }
        });

        if (targetItem) {
            // 変更を受け付けた後に prev を更新する（syncSelectValues では更新しない）
            sel.dataset.prev = newValue;
            swapItems(currentItem, targetItem);
        } else {
            // 対応する要素が見つからない場合は選択を元に戻す
            sel.value = oldValue;
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
                // 初回読み込み時に元の固有番号を記録する（送信時の復元用）
                if (!sel.dataset.originalNo) {
                    sel.dataset.originalNo = sel.value;
                }
                // prev の初期値も設定する（handleSelectChange の変更検知用）
                if (!sel.dataset.prev) {
                    sel.dataset.prev = sel.value;
                }
            }
        });

        updateCharaClasses();
        syncSelectValues();
    }

    // 初期化実行
    initPartySystem();

    // フォーム送信時に表示用番号を元の固有番号に差し替える
    const partyForm = partyContainer.closest("form");
    if (partyForm) {
        partyForm.addEventListener("submit", () => {
            changed = false;  // 送信による遷移では離脱警告を出さない
            prepareForSubmit();
        });
    }

});
