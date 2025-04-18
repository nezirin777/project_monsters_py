$(function() {
    // ソート関数
    function sortList(rel, order, isNumeric) {
        $('.list2').html(
            $('.list2_monster_table').sort(function(a, b) {
                var valueA = $(a).find('.' + rel).text();
                var valueB = $(b).find('.' + rel).text();

                // rel="upday" の場合、日付として比較
                if (rel === 'upday') {
                    // 日付文字列を Date オブジェクトに変換（例: "2024/12/25"）
                    var dateA = new Date(valueA.replace(/\//g, '-')); // "2024/12/25" -> "2024-12-25"
                    var dateB = new Date(valueB.replace(/\//g, '-')); // "2024/12/25" -> "2024-12-25"

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
                    valueA = Number(valueA);
                    valueB = Number(valueB);
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
        var rel = $(this).attr('rel'); // ソート対象クラス
        var order = $(this).data('order'); // 昇順 or 降順
        var isNumeric = $(this).data('numeric'); // 数値比較かどうか
        sortList(rel, order, isNumeric);
    });
});
