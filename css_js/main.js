// ボタンの多重クリック対策
document.addEventListener('DOMContentLoaded', () => {
    const SUBMIT_SELECTOR = 'button[type="submit"], input[type="submit"]';
    const ONCE_CLICK_SELECTOR = 'button[data-once-click], input[type="button"][data-once-click], input[type="submit"][data-once-click]';
    const DEFAULT_TIMEOUT = 10000; // 10秒

    function rememberButtonLabel(button) {
        if (!button) return;

        if (button.tagName === 'INPUT') {
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.value || '';
            }
        } else {
            if (!button.dataset.originalText) {
                button.dataset.originalText = button.textContent || '';
            }
        }
    }

    function setButtonLabel(button, text) {
        if (!button) return;

        if (button.tagName === 'INPUT') {
            button.value = text;
        } else {
            button.textContent = text;
        }
    }

    function setButtonProcessing(button, processing, processingText = '処理中...') {
        if (!button) return;

        rememberButtonLabel(button);

        button.disabled = processing;
        button.classList.toggle('submitting', processing);

        if (processing) {
            setButtonLabel(button, processingText);
        } else {
            setButtonLabel(button, button.dataset.originalText || '');
        }
    }

    function setButtonsProcessing(buttons, processing, processingText = '処理中...') {
        buttons.forEach(button => setButtonProcessing(button, processing, processingText));
    }

    function autoRestoreButtons(buttons, timeout = DEFAULT_TIMEOUT) {
        window.setTimeout(() => {
            buttons.forEach(button => {
                if (button && button.disabled) {
                    setButtonProcessing(button, false);
                }
            });
        }, timeout);
    }

    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', (event) => {
            const submitButton = form.querySelector(SUBMIT_SELECTOR);

            if (!submitButton || submitButton.disabled) {
                event.preventDefault();
                return;
            }

            const allSubmitButtons = Array.from(document.querySelectorAll(SUBMIT_SELECTOR));
            setButtonsProcessing(allSubmitButtons, true);
            autoRestoreButtons(allSubmitButtons);
        });
    });

    document.addEventListener('click', (event) => {
        const button = event.target.closest(ONCE_CLICK_SELECTOR);
        if (!button) return;

        if (button.disabled) {
            event.preventDefault();
            event.stopPropagation();
            return;
        }

        setButtonProcessing(button, true);
        autoRestoreButtons([button]);
    });

    // 外部スクリプトから使えるように公開
    window.setButtonProcessing = setButtonProcessing;
    window.setButtonsProcessing = setButtonsProcessing;
});

// 自動移動用 post 関数の最適化
function post(path, params, method = 'post') {
    if (!path || !params || typeof params !== 'object') {
        console.warn('Invalid path or parameters');
        return;
    }

    const form = document.createElement('form');
    form.method = method;
    form.action = path;

    Object.entries(params).forEach(([key, value]) => {
        const hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.name = key;
        hiddenField.value = value ?? '';
        form.appendChild(hiddenField);
    });

    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}
