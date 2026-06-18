"""In-browser selector picker overlay (uses same heuristics as recording)."""

from app.selector_heuristics import SELECTOR_HEURISTICS_JS

PICKER_INSTALL_SCRIPT = (
    """
(() => {
  if (window.__shopPickerActive) return;
  window.__shopPickerActive = true;
"""
    + SELECTOR_HEURISTICS_JS
    + """
  function textInputForPick(el) {
    if (!el || el.nodeType !== 1) return null;
    if (isTextInput(el) || el.tagName === 'TEXTAREA') return el;
    const label = el.closest('label');
    if (label) {
      const input = label.querySelector(
        'input:not([type="checkbox"]):not([type="radio"]), textarea'
      );
      if (input) return input;
    }
    return null;
  }

  function resolvePickTarget(rawEl) {
    if (!rawEl || rawEl.nodeType !== 1) return { el: null, selector: null };
    if (rawEl.id === '__shopPickerOverlay' || rawEl.id === '__shopPickerHint') {
      return { el: null, selector: null };
    }

    const checkbox = checkboxInputFor(rawEl);
    if (checkbox) {
      return {
        el: checkbox,
        selector: buildCheckboxSelector(checkbox) || buildSelector(checkbox),
      };
    }

    const canvas = canvasFor(rawEl);
    if (canvas) {
      return {
        el: canvas,
        selector: buildCanvasSelector(canvas) || buildSelector(canvas),
      };
    }

    const textInput = textInputForPick(rawEl);
    if (textInput) {
      return {
        el: textInput,
        selector: buildInputSelector(textInput) || buildSelector(textInput),
      };
    }

    return {
      el: rawEl,
      selector: buildSelector(rawEl),
    };
  }

  function removeOverlay() {
    document.getElementById('__shopPickerOverlay')?.remove();
    document.getElementById('__shopPickerHint')?.remove();
  }

  function showOverlay(el) {
    removeOverlay();
    const rect = el.getBoundingClientRect();
    const box = document.createElement('div');
    box.id = '__shopPickerOverlay';
    box.style.cssText = [
      'position:fixed',
      'pointer-events:none',
      'z-index:2147483646',
      `left:${rect.left}px`,
      `top:${rect.top}px`,
      `width:${rect.width}px`,
      `height:${rect.height}px`,
      'border:2px solid #5ec8f2',
      'background:rgba(79,195,247,0.12)',
      'border-radius:3px',
    ].join(';');
    document.body.appendChild(box);
  }

  const hint = document.createElement('div');
  hint.id = '__shopPickerHint';
  hint.textContent = 'Кликните по элементу · Esc — отмена';
  hint.style.cssText = [
    'position:fixed',
    'top:8px',
    'left:50%',
    'transform:translateX(-50%)',
    'z-index:2147483647',
    'background:#094771',
    'color:#fff',
    'padding:6px 12px',
    'border-radius:4px',
    'font:12px sans-serif',
    'pointer-events:none',
  ].join(';');
  document.body.appendChild(hint);

  function onMove(event) {
    const raw = document.elementFromPoint(event.clientX, event.clientY);
    const target = resolvePickTarget(raw);
    if (!target.el) return;
    showOverlay(target.el);
  }

  function onClick(event) {
    event.preventDefault();
    event.stopPropagation();
    const raw = document.elementFromPoint(event.clientX, event.clientY);
    const target = resolvePickTarget(raw);
    if (!target.el || !target.selector) return;
    const done = window.pickSelectorDone;
    if (typeof done === 'function') {
      Promise.resolve(done(target.selector)).catch(() => {});
    }
    window.__shopPickerCleanup && window.__shopPickerCleanup();
  }

  function onKey(event) {
    if (event.key === 'Escape') {
      const cancel = window.pickSelectorCancel;
      if (typeof cancel === 'function') {
        Promise.resolve(cancel()).catch(() => {});
      }
      window.__shopPickerCleanup && window.__shopPickerCleanup();
    }
  }

  window.__shopPickerCleanup = () => {
    document.removeEventListener('mousemove', onMove, true);
    document.removeEventListener('click', onClick, true);
    document.removeEventListener('keydown', onKey, true);
    removeOverlay();
    hint.remove();
    window.__shopPickerActive = false;
    delete window.__shopPickerCleanup;
  };

  document.addEventListener('mousemove', onMove, true);
  document.addEventListener('click', onClick, true);
  document.addEventListener('keydown', onKey, true);
})();
"""
)

PICKER_UNINSTALL_SCRIPT = """
(() => {
  if (typeof window.__shopPickerCleanup === 'function') {
    window.__shopPickerCleanup();
  }
})();
"""
