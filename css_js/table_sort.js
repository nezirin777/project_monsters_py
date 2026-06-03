// table_sort.js

document.addEventListener('DOMContentLoaded', () => {

    // ソート対象: テーブル本体ではなくラッパーdivを取得
    // （.haigou-sort-item-wrap が border-radius / shadow を持つ sortable 単位）
    const monsterTables = Array.from(document.querySelectorAll('.haigou-sort-item-wrap'));
    const container = document.querySelector('.haigou-sort-list');
    const groupHeaders = document.querySelectorAll('.haigou-sort-header');
    const sortButtons = document.querySelectorAll('.sort-btn');

    // このスクリプトが対象とする要素がなければ即終了（安全装置）
    if (!container) return;

    // 各ラッパーのデータを最初に1回だけ解析し、オブジェクトにキャッシュ（記憶）する。
    // sort() は破壊的変更のため、No 順への復元は location.reload() で行う（後述）
    const cachedData = monsterTables.map(wrap => {
        const dataSpan = wrap.querySelector('span[data-no]');

        let no = 0, upday = 0, floor = 0;

        if (dataSpan) {
            no    = Number(dataSpan.dataset.no) || 0;
            // 無効な日付文字列は NaN → 0（エポック）として扱い、ソート時は最古扱いにする
            upday = new Date(dataSpan.dataset.upday).getTime() || 0;
            floor = Number(dataSpan.dataset.floor) || 0;
        }

        return { element: wrap, no, upday, floor };
    });

    // ソート関数
    function sortList(rel, order) {
        if (rel === 'no') {
            // No 順はグループヘッダーの再挿入が複雑なため、
            // ページ再読み込みで初期状態（グループヘッダーつき）に戻す。
            // cachedData は sort() で破壊的に変更されているため、
            // 元の順序への復元も兼ねている
            location.reload();
            return;
        }

        // グループヘッダーを非表示にする
        groupHeaders.forEach(header => header.style.display = 'none');

        // DOMを直接触らず、キャッシュしたメモリ上の配列だけをソートする（超高速）
        cachedData.sort((a, b) => {
            const valA = a[rel];
            const valB = b[rel];

            if (valA !== valB) {
                // asc（昇順）なら A - B、desc（降順）なら B - A
                return order === 'asc' ? (valA - valB) : (valB - valA);
            }

            // 値が同じ場合は、必ずNo（図鑑番号）でサブソートして順序を安定させる
            return a.no - b.no;
        });

        // ソートが終わった配列の順番に従って、HTML要素を一気に再配置
        // （Fragment使用で再描画を1回に抑える）
        const fragment = document.createDocumentFragment();
        cachedData.forEach(data => fragment.appendChild(data.element));
        container.appendChild(fragment);
    }

    // 各ボタンにクリックイベントを設定
    sortButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 今どのボタンが押されているかを視覚化（クラス付け替え）
            sortButtons.forEach(btn => btn.classList.remove('sort-btn--active'));
            button.classList.add('sort-btn--active');

            const rel   = button.getAttribute('rel');
            const order = button.dataset.order;

            sortList(rel, order);
        });
    });
});
