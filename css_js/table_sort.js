$(function() {
    // 値取得用関数（data属性優先、なければ従来のclass検索）
    function getValue(el, rel) {
        var target = $(el).find('[data-' + rel + ']');

        if (target.length) {
            return target.data(rel);
        }

        // fallback（旧構造用）
        return $(el).find('.' + rel).text();
    }

    // ソート関数
    function sortList(rel, order, isNumeric) {
        $('.list2').html(
            $('.list2_monster_table').sort(function(a, b) {

                var valueA = getValue(a, rel);
                var valueB = getValue(b, rel);

                // rel="upday" の場合、日付として比較
                if (rel === 'upday') {
                    // 日付文字列を Date オブジェクトに変換（例: "2024/12/25"）
                    var dateA = new Date(valueA);
                    var dateB = new Date(valueB);

                    if (order === 'asc') {
                        // 古い順（昇順）
                        if (dateA < dateB) return -1;
                        if (dateA > dateB) return 1;
                        return 0;
                    } else {
                        // 新しい順（降順）
                        if (dateA > dateB) return -1;
                        if (dateA < dateB) return 1;
                        return 0;
                    }
                }

                // 数値で比較する場合
                if (isNumeric) {
                    valueA = Number(valueA) || 0;
                    valueB = Number(valueB) || 0;
                } else {
                    valueA = String(valueA);
                    valueB = String(valueB);
                }

                // 並び順の設定（文字列または数値比較）
                if (order === 'asc') {
                    if (valueA < valueB) return -1;
                    if (valueA > valueB) return 1;
                    return 0;
                } else {
                    if (valueA > valueB) return -1;
                    if (valueA < valueB) return 1;
                    return 0;
                }
            })
        );
    }

    // ボタンクリックイベントを統一
    $('.sortBtn').on('click', function() {
        var rel = $(this).attr('rel'); // ソート対象クラス or data属性
        var order = $(this).data('order'); // 昇順 or 降順
        var isNumeric = $(this).data('numeric'); // 数値比較かどうか
        sortList(rel, order, isNumeric);
    });
});
