// table_sort.js

document.addEventListener('DOMContentLoaded', () => {

    // ソート対象の全テーブル要素を配列として取得
    const monsterTables = Array.from(document.querySelectorAll('.list2_monster_table'));
    const container = document.querySelector('.list2');
    const groupHeaders = document.querySelectorAll('.list2_group_header');
    const sortButtons = document.querySelectorAll('.sortBtn');

    // 爆速化。各テーブルのデータを最初に1回だけ解析し、オブジェクトにキャッシュ（記憶）する
    const cachedData = monsterTables.map(table => {
        // テーブル内のデータが埋め込まれている span を探す
        const dataSpan = table.querySelector('span[data-no]');

        let no = 0, upday = 0, floor = 0;

        if (dataSpan) {
            no = Number(dataSpan.dataset.no) || 0;
            // 日付はミリ秒に変換。無効な場合は0
            upday = new Date(dataSpan.dataset.upday).getTime() || 0;
            floor = Number(dataSpan.dataset.floor) || 0;
        }

        return {
            element: table, // 元のHTML要素
            no: no,
            upday: upday,
            floor: floor
        };
    });

    // ソート関数
    function sortList(rel, order) {
        // No順（デフォルト）の場合はリロードして初期状態（グループヘッダー付き）に戻す
        if (rel === 'no') {
            location.reload();
            return;
        }

        // グループヘッダーを非表示にする
        groupHeaders.forEach(header => header.style.display = 'none');

        // DOMを直接触らず、キャッシュしたメモリ上の配列だけをソートする（超高速）
        cachedData.sort((a, b) => {
            let valA = a[rel];
            let valB = b[rel];

            if (valA !== valB) {
                // asc（昇順）なら A - B、desc（降順）なら B - A
                return order === 'asc' ? (valA - valB) : (valB - valA);
            }

            // 値が同じ場合は、必ずNo（図鑑番号）でサブソートして順序を安定させる
            return a.no - b.no;
        });

        // ソートが終わった配列の順番に従って、HTML要素を一気に再配置（Fragment使用で再描画を1回に抑える）
        const fragment = document.createDocumentFragment();
        cachedData.forEach(data => fragment.appendChild(data.element));
        container.appendChild(fragment);
    }

    // 各ボタンにクリックイベントを設定
    sortButtons.forEach(button => {
        button.addEventListener('click', function() {
            // ★改善2: 今どのボタンが押されているかを視覚化（クラス付け替え）
            sortButtons.forEach(btn => btn.classList.remove('active-sort'));
            this.classList.add('active-sort');

            const rel = this.getAttribute('rel');
            const order = this.dataset.order;

            // isNumeric の判定は、キャッシュ時に全て数値化(getTime等)したため不要になりました
            sortList(rel, order);
        });
    });
});
