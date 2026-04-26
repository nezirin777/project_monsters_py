// img_change.js - プルダウン選択モンスター画像切り替え用

// <option value="{{ haigou.index }}" data-name="{{ haigou.name }}">{{ haigou.index }}: {{ haigou.name }} </option>
//上記のように、option要素のdata-name属性にモンスター名をセットしておく必要があります。

function change_img(selectName, imgName) {
    const form = document.forms["img_change"];
    const select = form?.[selectName];
    const img = form?.[imgName];

    if (!form || !select || !img) {
        console.warn(`Form, select, or image missing: ${selectName}, ${imgName}`);
        return;
    }

    // 選択されたオプション要素を取得
    const selectedOption = select.options[select.selectedIndex];

    // data-name属性からモンスター名を取得（未選択時は "0" にする）
    const m_name = selectedOption.getAttribute("data-name") || "0";

    // 現在のimg要素のsrcからディレクトリまでのパスを抽出
    // (例: "http://.../img/0.gif" -> "http://.../img")
    const basePath = img.src.substring(0, img.src.lastIndexOf('/'));

    // 新しい画像のパスをセット
    img.src = `${basePath}/${m_name}.gif`;
    img.alt = selectedOption.text;
}
