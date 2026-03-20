const {
  Connection,
  PublicKey,
  Transaction,
  TransactionInstruction,
} = solanaWeb3;

// -----------------------
// JSON埋め込み設定の読み込み
// -----------------------

// テンプレートに埋め込まれた商品定義JSONを読む
const shopItemsEl = document.getElementById("shop-items-json");
const ITEMS = shopItemsEl ? JSON.parse(shopItemsEl.textContent) : {};

// テンプレートに埋め込まれた共通設定JSONを読む
const shopConfigEl = document.getElementById("shop-config-json");
const SHOP_CONFIG = shopConfigEl ? JSON.parse(shopConfigEl.textContent) : {};

// -----------------------
// ネットワーク切り替え
// -----------------------

// mainnet / devnet を設定から決める
const NETWORK = SHOP_CONFIG.network || "devnet"; // "devnet" or "mainnet"

// 利用ネットワークごとの mint を切り替える
const TOKEN_MINT = NETWORK === "mainnet"
  ? SHOP_CONFIG.token_mint_mainnet
  : SHOP_CONFIG.token_mint_devnet;

// トークン小数桁数
const DECIMALS = Number(SHOP_CONFIG.token_decimals ?? 6);

// ショップ受取ウォレット
const SHOP_WALLET = SHOP_CONFIG.shop_wallet;

// Program IDs
// mainnet / devnet で使うトークンプログラムを切り替える
const TOKEN_PROGRAM_ID_USED = new PublicKey(
  NETWORK === "mainnet"
    ? SHOP_CONFIG.token_program_id_mainnet
    : SHOP_CONFIG.token_program_id_devnet
);

// ATA導出用プログラム
const ASSOCIATED_TOKEN_PROGRAM_ID = new PublicKey(
  SHOP_CONFIG.associated_token_program_id
);

// System Program
const SYSTEM_PROGRAM_ID = new PublicKey(
  SHOP_CONFIG.system_program_id
);

// Rent Sysvar
const RENT_SYSVAR = new PublicKey(
  SHOP_CONFIG.rent_sysvar
);

// HTTP only
// ブラウザ側は mainnet では proxy、devnet では直RPC を使う
const connection = new Connection(
  NETWORK === "mainnet"
    ? (SHOP_CONFIG.rpc_mainnet_proxy || "./rpc_proxy.py")
    : SHOP_CONFIG.rpc_devnet,
  "confirmed"
);

// 購入中フラグ（多重実行防止）
let buying = false;
// トースト自動消去タイマー
let toastTimer = null;

function ensureUiElements() {
  // ステータス表示用要素が無ければ作る
  let statusBox = document.getElementById("wallet_status_box");
  if (!statusBox) {
    statusBox = document.createElement("div");
    statusBox.id = "wallet_status_box";
    document.body.appendChild(statusBox);
  }

  // トースト表示用要素が無ければ作る
  let toastBox = document.getElementById("wallet_toast");
  if (!toastBox) {
    toastBox = document.createElement("div");
    toastBox.id = "wallet_toast";
    document.body.appendChild(toastBox);
  }
}

function showStatus(msg) {
  // 進行状況を画面中央付近のステータス表示へ出す
  console.log(`[Phantom] ${msg}`);
  ensureUiElements();
  const box = document.getElementById("wallet_status_box");
  box.textContent = msg;
  box.style.display = "block";
}

function hideStatus() {
  // ステータス表示を消す
  const box = document.getElementById("wallet_status_box");
  if (!box) return;
  box.textContent = "";
  box.style.display = "none";
}

function showToast(msg, duration = 3000) {
  // 一時通知を表示して自動で消す
  console.log(`[Toast] ${msg}`);
  ensureUiElements();

  const toast = document.getElementById("wallet_toast");
  if (toastTimer) {
    clearTimeout(toastTimer);
    toastTimer = null;
  }

  toast.textContent = msg;
  toast.style.display = "block";

  toastTimer = setTimeout(() => {
    toast.textContent = "";
    toast.style.display = "none";
    toastTimer = null;
  }, duration);
}

function normalizeError(err) {
  // 例外オブジェクトを表示しやすい文字列へ変換する
  if (!err) return "不明なエラー";
  if (typeof err === "string") return err;
  return err.message || JSON.stringify(err);
}

function postToMyPage() {
  // token を引き継いでマイページへ POST で戻る
  const token = document.getElementById("page_token")?.value || "";
  const action = document.getElementById("cgi_url")?.value || "./login.py";

  const form = document.createElement("form");
  form.method = "POST";
  form.action = action;

  const fields = {
    mode: "my_page",
    token,
  };

  for (const [key, value] of Object.entries(fields)) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = key;
    input.value = value;
    form.appendChild(input);
  }

  document.body.appendChild(form);
  form.submit();
}

async function getATA(owner, mint) {
  // owner と mint から Associated Token Account を導出する
  const [ata] = await PublicKey.findProgramAddress(
    [owner.toBuffer(), TOKEN_PROGRAM_ID_USED.toBuffer(), mint.toBuffer()],
    ASSOCIATED_TOKEN_PROGRAM_ID
  );
  return ata;
}

function createATAIx(payer, ata, owner, mint) {
  // ATA 未作成時に新規作成する命令を組み立てる
  return new TransactionInstruction({
    programId: ASSOCIATED_TOKEN_PROGRAM_ID,
    keys: [
      { pubkey: payer, isSigner: true, isWritable: true },
      { pubkey: ata, isSigner: false, isWritable: true },
      { pubkey: owner, isSigner: false, isWritable: false },
      { pubkey: mint, isSigner: false, isWritable: false },
      { pubkey: SYSTEM_PROGRAM_ID, isSigner: false, isWritable: false },
      { pubkey: TOKEN_PROGRAM_ID_USED, isSigner: false, isWritable: false },
      { pubkey: RENT_SYSVAR, isSigner: false, isWritable: false },
    ],
    data: new Uint8Array([]),
  });
}

function createTransferCheckedIx(source, mint, dest, owner, amount, decimals) {
  // transferChecked 命令を手組みする
  const data = new Uint8Array(10);
  const view = new DataView(data.buffer);

  view.setUint8(0, 12);
  view.setBigUint64(1, BigInt(amount), true);
  view.setUint8(9, decimals);

  return new TransactionInstruction({
    programId: TOKEN_PROGRAM_ID_USED,
    keys: [
      { pubkey: source, isSigner: false, isWritable: true },
      { pubkey: mint, isSigner: false, isWritable: false },
      { pubkey: dest, isSigner: false, isWritable: true },
      { pubkey: owner, isSigner: true, isWritable: false },
    ],
    data,
  });
}

function parseUiAmountToRaw(uiAmount, decimals) {
  // 人間向けの価格文字列を最小単位整数へ変換する
  const [intPart, fracPart = ""] = String(uiAmount).split(".");
  const frac = fracPart.padEnd(decimals, "0").slice(0, decimals);
  const raw = `${intPart}${frac}`.replace(/^0+(?=\d)/, "");
  return raw || "0";
}

function buySelectedItem() {
  // ラジオで選択中の商品IDを取得して購入処理へ渡す
  const selected = document.querySelector('input[name="buy_item"]:checked');

  if (!selected) {
    showToast("購入するアイテムを選んでください", 3000);
    return;
  }

  buyItem(selected.value);
}

async function buyItem(itemId) {
  // 商品を1件購入する本体処理
  if (buying) return;

  // 商品定義が無ければ中止
  const item = ITEMS[itemId];
  if (!item) {
    showToast(`未定義の商品です: ${itemId}`, 4000);
    return;
  }

  // 多重実行を防ぐ
  buying = true;

  try {
    ensureUiElements();

    // Phantom が無ければ中止
    if (!window.solana?.isPhantom) {
      showToast(
        "Phantom Walletが必要です。" +
          (NETWORK === "devnet" ? "Devnet" : "Mainnet") +
          " に切り替えてください。",
        4000
      );
      return;
    }

    const provider = window.solana;

    // ウォレット接続を要求する
    showStatus(`ウォレットを起動しています…\n購入商品: ${item.name}`);
    const resp = await provider.connect();
    const user = new PublicKey(resp.publicKey.toString());

    // mint / shop 情報を準備する
    showStatus(`購入情報を準備しています…\n購入商品: ${item.name}`);
    const mint = new PublicKey(TOKEN_MINT);
    const shop = new PublicKey(SHOP_WALLET);

    // 購入者とショップの ATA を導出する
    const userATA = await getATA(user, mint);
    const shopATA = await getATA(shop, mint);

    // mint アカウントの存在確認
    showStatus("対象トークンを確認しています…");
    const mintInfo = await connection.getAccountInfo(mint);
    if (!mintInfo) {
      hideStatus();
      showToast(
        NETWORK === "devnet"
          ? "Devnet上に対象ミントが見つかりません。"
          : "Mainnet上に対象ミントが見つかりません。",
        4000
      );
      return;
    }

    // 購入者の ATA 存在確認
    showStatus("ウォレット口座を確認しています…");
    const userAccount = await connection.getAccountInfo(userATA);
    if (!userAccount) {
      hideStatus();
      showToast(
        "あなたのトークン口座(ATA)が見つかりません。対象トークンを一度受け取って口座を作成してください。",
        4500
      );
      return;
    }

    // ショップの ATA 存在確認
    showStatus("ショップ口座を確認しています…");
    const shopAccount = await connection.getAccountInfo(shopATA);

    // トランザクション本体を作成する
    const tx = new Transaction();
    const amountRaw = parseUiAmountToRaw(item.price, DECIMALS);

    // ショップ ATA が無ければ自動作成命令を先頭に入れる
    if (!shopAccount) {
      showStatus("ショップ受取口座を準備しています…");
      tx.add(createATAIx(user, shopATA, shop, mint));
    }

    // ユーザー残高を確認する
    showStatus("残高を確認しています…");
    const bal = await connection.getTokenAccountBalance(userATA);
    if (BigInt(bal.value.amount) < BigInt(amountRaw)) {
      hideStatus();
      showToast("残高不足です", 3000);
      return;
    }

    // 実際の送金命令を追加する
    tx.add(
      createTransferCheckedIx(
        userATA,
        mint,
        shopATA,
        user,
        amountRaw,
        DECIMALS
      )
    );

    // 手数料負担者を購入者に設定する
    tx.feePayer = user;

    // 最新 blockhash を取得してトランザクションへ埋め込む
    showStatus("送金トランザクションを作成しています…");
    const { blockhash } = await connection.getLatestBlockhash("confirmed");
    tx.recentBlockhash = blockhash;

    // 送信オプション
    const sendOptions = {
      skipPreflight: false,
      preflightCommitment: "confirmed",
      maxRetries: 3,
    };

    // Phantom 上で署名＆送信してもらう
    showStatus("ウォレットで送金承認を待っています…");
    const result = await provider.signAndSendTransaction(tx, sendOptions);
    const signature = result.signature;

    // サーバー側確認処理へ txid を渡す
    showStatus("送金シグネチャを取得しました。サーバーで確認しています…");
    const params = new URLSearchParams({
      txid: signature,
      item: String(itemId),
      user: user.toBase58(),
      user_name: document.getElementById("user_name")?.value || "",
      network: NETWORK,
    });

    const res = await fetch("./vips_check.py", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: params.toString(),
    });

    // サーバーからの結果テキストを受け取る
    const text = await res.text();

    // 表示用に改行ごとへ分解する
    const lines = text
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);

    // 内部用メッセージを除いてユーザー向け文を作る
    const userText = lines
      .filter((line) => line !== "OK" && line !== "purchase success")
      .join("\n");

    if (!res.ok) {
      hideStatus();
      showToast("サーバー確認処理でエラーが発生しました。error_log を確認してください。", 6000);
      console.error("vips_check failed:", res.status, text);
      return;
    }

    // 成功時はトースト表示の後にマイページへ戻る
    if (text.includes("OK")) {
      showStatus("購入完了。マイページへ移動します…");
      showToast(userText || `${item.name} を付与しました`, 1800);
      setTimeout(() => {
        postToMyPage();
      }, 900);
    } else {
      // 失敗時はサーバー文言を表示する
      hideStatus();
      showToast(userText || "購入処理に失敗しました", 6000);
    }
  } catch (err) {
    // 例外発生時は画面にエラーメッセージを出す
    console.error(err);
    hideStatus();
    showToast(`エラー: ${normalizeError(err)}`, 6000);
  } finally {
    // 成否に関係なく多重実行フラグを戻す
    buying = false;
  }
}

// 購入処理中のページ離脱を警告する
window.addEventListener("beforeunload", (event) => {
  if (!buying) return;

  event.preventDefault();
  event.returnValue = "";
});

document.addEventListener("click", (event) => {
  if (!buying) return;

  const link = event.target.closest("a");
  if (!link) return;

  event.preventDefault();
  showToast("購入処理中はページ移動できません", 2500);
});

// HTML の onclick から呼べるように公開する
window.buyItem = buyItem;
window.buySelectedItem = buySelectedItem;
