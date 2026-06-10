// css_js/game_theme.js

(() => {
  'use strict';

  const STORAGE_KEY  = 'monsters_theme';
  const VALID_THEMES = ['default', 'retro', 'cyber', 'oldweb'];
  const ATTR         = 'data-monsters-theme';

  // ==========================================
  // テーマ適用
  // ==========================================

  function applyTheme(theme) {
    const safe = VALID_THEMES.includes(theme) ? theme : 'default';

    if (safe === 'default') {
      // デフォルトは属性自体を除去する（game.css / common.css のみが効く状態）
      document.body.removeAttribute(ATTR);
    } else {
      document.body.setAttribute(ATTR, safe);
    }

    // 選択ボタンのアクティブ状態を更新する
    document.querySelectorAll('.monsters-theme-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.theme === safe);
    });
  }

  function saveTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // プライベートブラウジング等でストレージが使えない環境では無視する
    }
  }

  function loadTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY) || 'default';
    } catch {
      return 'default';
    }
  }

  // ==========================================
  // 初期化
  // ==========================================

  // <head> 内の script タグより先に body が存在しない可能性があるため
  // DOMContentLoaded を待たずにインラインで実行する。
  // ただし body が存在しない場合は DOMContentLoaded まで待つ。
  function init() {
    const saved = loadTheme();
    applyTheme(saved);
    bindButtons();
  }

  // ==========================================
  // ボタンへのイベント設定
  // ==========================================

  function bindButtons() {
    // DOMContentLoaded 後に呼ばれることを想定しているが、
    // 動的に追加されたボタンにも対応するため document 全体に委譲する
    document.addEventListener('click', e => {
      // 1. テーマ切り替えボタンの判定
      const btn = e.target.closest('.monsters-theme-btn');
      if (btn) {
        const theme = btn.dataset.theme || 'default';
        applyTheme(theme);
        saveTheme(theme);
        return;
      }

      // 2. フローティングメニューの開閉トグル判定
      const trigger = e.target.closest('.monsters-theme-trigger');
      if (trigger) {
        const floater = trigger.closest('.monsters-theme-floater');
        if (floater) {
          floater.classList.toggle('open');
        }
        return;
      }

      // 3. メニュー外をクリックした場合は閉じる
      if (!e.target.closest('.monsters-theme-floater')) {
        document.querySelectorAll('.monsters-theme-floater').forEach(f => {
          f.classList.remove('open');
        });
      }
    });
  }

  // body が存在するタイミングで即時適用する（FOUC防止）
  if (document.body) {
    init();
  } else {
    document.addEventListener('DOMContentLoaded', init);
  }

})();
