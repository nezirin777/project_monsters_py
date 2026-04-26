$(function() {
    // 値取得用関数（data属性優先、なければ従来のclass検索）
    function getValue(el, rel) {
        var target = $(el).find('[data-' + rel + ']');
        if (target.length) {
            return target.data(rel);
        }
        return $(el).find('.' + rel).text();
    }

    // ソート関数
    function sortList(rel, order, isNumeric) {
        // No順（デフォルト）の場合は、ページをリロードして初期状態（種族ヘッダー付き）に戻すのが一番きれいです
        if (rel === 'no') {
            location.reload();
            return;
        }

        // それ以外のソート時は、種族ごとのグループヘッダーは意味を持たないので非表示にする
        $('.list2_group_header').hide();

        // テーブル要素のソート
        var sortedElements = $('.list2_monster_table').sort(function(a, b) {
            var valueA = getValue(a, rel);
            var valueB = getValue(b, rel);

            // rel="upday" の場合、日付を安全に比較
            if (rel === 'upday') {
                // 有効な日付ならミリ秒に、無効なら0にする
                var dateA = new Date(valueA).getTime() || 0;
                var dateB = new Date(valueB).getTime() || 0;

                if (dateA !== dateB) {
                    return (order === 'asc') ? (dateA - dateB) : (dateB - dateA);
                }
            }
            // 数値で比較する場合
            else if (isNumeric) {
                valueA = Number(valueA) || 0;
                valueB = Number(valueB) || 0;

                if (valueA !== valueB) {
                    return (order === 'asc') ? (valueA - valueB) : (valueB - valueA);
                }
            }
            // 文字列で比較する場合
            else {
                valueA = String(valueA);
                valueB = String(valueB);

                if (valueA !== valueB) {
                    if (order === 'asc') {
                        return (valueA < valueB) ? -1 : 1;
                    } else {
                        return (valueA > valueB) ? -1 : 1;
                    }
                }
            }

            // 【重要】値が同じだった場合は、必ず「No（図鑑番号など）」でサブソートして順序を安定させる
            var noA = Number(getValue(a, 'no')) || 0;
            var noB = Number(getValue(b, 'no')) || 0;
            return noA - noB;
        });

        // .html()ではなく .append() を使うことで、要素に関連付けられたイベントなどを壊さずに移動できます
        $('.list2').append(sortedElements);
    }

    // ボタンクリックイベント
    $('.sortBtn').on('click', function() {
        var rel = $(this).attr('rel');
        var order = $(this).data('order');
        var isNumeric = $(this).data('numeric');
        sortList(rel, order, isNumeric);
    });
});
