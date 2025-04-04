$(function() {
    // ソート関数
    function sortList(rel, order, isNumeric) {
        $('.list').html(
            $('#tuika_mob_list .table_m_box').sort(function(a, b) {
                var valueA = $(a).find('.' + rel).text();
                var valueB = $(b).find('.' + rel).text();

                // 数値で比較する場合
                if (isNumeric) {
                    valueA = Number(valueA);
                    valueB = Number(valueB);
                }

                // 並び順の設定
                if (order === 'asc') {
                    return valueA > valueB ? 1 : -1;
                } else {
                    return valueA < valueB ? 1 : -1;
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
