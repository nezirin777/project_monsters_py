document.addEventListener("DOMContentLoaded", function () {
    // フォーム要素を取得
    const form = document.getElementById("form_check");
    // フォームが存在するか確認
    if (!form) {
        console.error("フォームが見つかりません");
        return;
    }
    // フォームの送信イベントにリスナーを追加
    form.addEventListener("submit", function (e) {
        // 選択されたラジオボタンを取得
        const selected = document.querySelector("input[name='m_name']:checked");
        if (!selected) {
            // ラジオボタンが選択されていない場合、警告を表示して送信をキャンセル
            alert("モンスターを選択してください。");
            e.preventDefault();
            return;
        }
        // 確認ダイアログを表示
        const confirmation = confirm(
            `「${selected.value}」を選択しました。交換を実行しますか？`
        );
        if (!confirmation) {
            // キャンセルされた場合、送信をキャンセル
            e.preventDefault();
        }
    });
});
