// ボタンの多重クリック対策
$(document).ready(function () {
    $("form").submit(function (event) {
        const submitButton = $(":submit");
        if (submitButton.prop("disabled")) {
            // 多重クリックを防止
            event.preventDefault();
            return false;
        }
        submitButton.prop("disabled", true);
        setTimeout(() => {
            submitButton.prop("disabled", false);
        }, 20000); // 必要に応じて時間を調整
    });
});


// 自動移動用 post 関数の最適化
function post(path, params, method = 'post') {
    const form = document.createElement('form');
    form.method = method;
    form.action = path;

    Object.entries(params).forEach(([key, value]) => {
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = key;
        hiddenField.value = value;
        form.appendChild(hiddenField);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form); // DOMをクリーンアップ
}

// メニュー鍵、特技一覧開閉
function bo(a, b) {
    document.getElementById(b).style.display = "none";
    const element = document.getElementById(a);
    element.style.display = (element.style.display === "block") ? "none" : "block";
}


//プルダウン選択モンスター画像切り替え用
let Images = []; // グローバルで配列を初期化

function main(imgpath, pt, m_name) {
    pt = pt.split("/");
    pt[0] = m_name ? m_name : "0";

    for (let i = 0; i < pt.length; i++) {
        Images[i] = new Image();
        Images[i].src = imgpath + pt[i] + ".gif";
    }
}

function change_img1() {
	form1.img1.src = Images[ form1.haigou1.options[form1.haigou1.selectedIndex].value ].src;
}
function change_img2() {
	form1.img2.src = Images[ form1.haigou2.options[form1.haigou2.selectedIndex].value ].src;
}
//mget,park
function change_img() {
	form1.img1.src = Images[form1.Mno.selectedIndex].src;
}
