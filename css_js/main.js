// ボタンの多重クリック対策
$(document).ready(function () {
    $("form").submit(function (event) {
        const submitButton = $(":submit"); // フォーム内のsubmitボタンを対象
        if (!submitButton.length) {
            event.preventDefault();
            return false; // 送信ボタンが存在しない場合
        }
        if (submitButton.prop("disabled")) {
            event.preventDefault();
            return false; // 多重クリック防止
        }
        submitButton.prop("disabled", true);
        setTimeout(() => {
            submitButton.prop("disabled", false);
        }, 20000); // 必要に応じて時間を調整
    });
});

// 自動移動用 post 関数の最適化
function post(path, params, method = 'post') {
    if (!path || !params || typeof params !== 'object') {
        console.warn('Invalid path or parameters');
        return; // パスまたはパラメータが無効な場合
    }

    const form = document.createElement('form');
    form.method = method;
    form.action = path;

    Object.entries(params).forEach(([key, value]) => {
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = key;
        hiddenField.value = value ?? ''; // null/undefinedを空文字に変換
        form.appendChild(hiddenField);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form); // DOMをクリーンアップ
}

// メニュー鍵、特技一覧開閉
function bo(a, b) {
    const elementB = document.getElementById(b);
    const elementA = document.getElementById(a);

    if (!elementA || !elementB) {
        console.warn('One or both elements not found:', a, b);
        return; // 要素が存在しない場合
    }

    elementB.style.display = "none";
    elementA.style.display = elementA.style.display === "block" ? "none" : "block";
}

// プルダウン選択モンスター画像切り替え用
let Images = []; // グローバルで配列を初期化

function main(imgpath, pt, m_name) {
    if (!imgpath || !pt) {
        return; // パスまたはパラメータが無効
    }

    pt = pt.split("/");
    pt[0] = m_name || "0"; // m_nameがfalsyなら"0"

    Images = []; // 配列をリセット
    for (let i = 0; i < pt.length; i++) {
        Images[i] = new Image();
        Images[i].src = imgpath + pt[i] + ".gif";
    }
}

function change_img1() {
    const form = document.forms['form1'];
    const haigou1 = form?.haigou1;
    const img1 = form?.img1;
    if (!form || !haigou1 || !img1 || !Images[haigou1.options[haigou1.selectedIndex]?.value]) {
        return; // フォームまたは画像が存在しない
    }
    img1.src = Images[haigou1.options[haigou1.selectedIndex].value].src;
}

function change_img2() {
    const form = document.forms['form1'];
    const haigou2 = form?.haigou2;
    const img2 = form?.img2;
    if (!form || !haigou2 || !img2 || !Images[haigou2.options[haigou2.selectedIndex]?.value]) {
        return; // フォームまたは画像が存在しない
    }
    img2.src = Images[haigou2.options[haigou2.selectedIndex].value].src;
}

function change_img() {
    const form = document.forms['form1'];
    const Mno = form?.Mno;
    const img1 = form?.img1;
    if (!form || !Mno || !img1 || !Images[Mno.selectedIndex]) {
        return; // フォームまたは画像が存在しない
    }
    img1.src = Images[Mno.selectedIndex].src;
}
