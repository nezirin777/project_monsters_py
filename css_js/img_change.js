
// プルダウン選択モンスター画像切り替え用
Images = []; // グローバルで配列を初期化

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

function change_img(selectName, imgName, useValue = true) {
    const form = document.forms["img_change"];
    const select = form?.[selectName];
    const img = form?.[imgName];
    if (!form || !select || !img) {
        console.warn(`Form, select, or image missing: ${selectName}, ${imgName}`);
        return;
    }
    const index = useValue ? select.options[select.selectedIndex]?.value : select.selectedIndex;
    if (!index || !Images[index]) {
        console.warn(`Image data not found for index: ${index}`);
        img.src = `${form.querySelector('img').src.split('/').slice(0, -1).join('/')}/0.gif`; // デフォルト画像
        return;
    }
    img.src = Images[index].src;
    img.alt = select.options[select.selectedIndex]?.text || `${selectName} モンスター`;
}
