"""In-browser selector picker overlay (uses same heuristics as recording)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.selector_heuristics import SELECTOR_HEURISTICS_JS

if TYPE_CHECKING:
    from playwright.sync_api import Frame, Page

PICKER_INSTALL_SCRIPT = (
    """
(() => {
  if (typeof window.__shopPickerCleanup === 'function') {
    window.__shopPickerCleanup();
  }
  if (window.__shopPickerActive) return;
  if (window !== window.top) return;
  window.__shopPickerActive = true;
"""
    + SELECTOR_HEURISTICS_JS
    + """
  const SHIELD_ID = '__shopPickerShield';
  const OVERLAY_ID = '__shopPickerOverlay';
  const HINT_ID = '__shopPickerHint';
  const SKIP_IDS = new Set([SHIELD_ID, OVERLAY_ID, HINT_ID]);

  function buildIframeSelector(el) {
    if (!el || el.tagName !== 'IFRAME') return null;
    const src = el.getAttribute('src') || '';
    if (src.includes('telegram.org')) {
      return 'iframe[src*="telegram.org"]';
    }
    if (el.id) return `#${cssEscape(el.id)}`;
    const title = el.getAttribute('title');
    if (title) return `iframe[title="${cssEscape(title)}"]`;
    const name = el.getAttribute('name');
    if (name) return `iframe[name="${cssEscape(name)}"]`;
    try {
      const url = new URL(src, window.location.href);
      if (url.host) {
        return `iframe[src*="${cssEscape(url.host)}"]`;
      }
    } catch (e) {
      /* ignore */
    }
    return buildSelector(el);
  }

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
    if (SKIP_IDS.has(rawEl.id)) {
      return { el: null, selector: null };
    }

    if (rawEl.tagName === 'IFRAME') {
      return {
        el: rawEl,
        selector: buildIframeSelector(rawEl) || buildSelector(rawEl),
      };
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

  function elementUnderPointer(x, y) {
    const stack = document.elementsFromPoint(x, y);
    for (const el of stack) {
      if (!el || el.nodeType !== 1) continue;
      if (SKIP_IDS.has(el.id)) continue;
      return el;
    }
    return null;
  }

  function removeOverlay() {
    document.getElementById(OVERLAY_ID)?.remove();
  }

  function showOverlay(el) {
    removeOverlay();
    const rect = el.getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    const box = document.createElement('div');
    box.id = OVERLAY_ID;
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
  hint.id = HINT_ID;
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

  function updateHint(target) {
    if (target.el && target.el.tagName === 'IFRAME') {
      hint.textContent =
        'Клик — выбрать iframe (внутри стороннего виджета, например Telegram)';
      return;
    }
    hint.textContent = 'Кликните по элементу · Esc — отмена';
  }

  function finishPick(selector) {
    const done = window.pickSelectorDone;
    if (typeof done === 'function') {
      Promise.resolve(done(selector)).catch(() => {});
    }
    window.__shopPickerCleanup && window.__shopPickerCleanup();
  }

  function onMove(event) {
    const raw = elementUnderPointer(event.clientX, event.clientY);
    const target = resolvePickTarget(raw);
    if (!target.el) return;
    showOverlay(target.el);
    updateHint(target);
  }

  function onPick(event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    const raw = elementUnderPointer(event.clientX, event.clientY);
    const target = resolvePickTarget(raw);
    if (!target.el || !target.selector) return;
    finishPick(target.selector);
  }

  function blockPointerDown(event) {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
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

  let shield = null;
  shield = document.createElement('div');
  shield.id = SHIELD_ID;
  shield.style.cssText = [
    'position:fixed',
    'inset:0',
    'z-index:2147483645',
    'cursor:crosshair',
    'background:transparent',
  ].join(';');
  document.body.appendChild(shield);
  shield.addEventListener('pointerdown', blockPointerDown, true);
  shield.addEventListener('mousedown', blockPointerDown, true);
  shield.addEventListener('mousemove', onMove, true);
  shield.addEventListener('click', onPick, true);

  window.__shopPickerCleanup = () => {
    shield.removeEventListener('pointerdown', blockPointerDown, true);
    shield.removeEventListener('mousedown', blockPointerDown, true);
    shield.removeEventListener('mousemove', onMove, true);
    shield.removeEventListener('click', onPick, true);
    shield.remove();
    shield = null;
    document.removeEventListener('keydown', onKey, true);
    removeOverlay();
    hint.remove();
    window.__shopPickerActive = false;
    delete window.__shopPickerCleanup;
  };

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


def install_picker_in_all_frames(page: Page) -> None:
    """Install picker on the main frame only (shield pierces into iframes)."""
    _install_picker_in_frame(page.main_frame)


def uninstall_picker_from_all_frames(page: Page) -> None:
    _uninstall_picker_in_frame(page.main_frame)
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        _uninstall_picker_in_frame(frame)


def _install_picker_in_frame(frame: Frame) -> None:
    try:
        if frame.is_detached():
            return
        frame.evaluate(PICKER_INSTALL_SCRIPT)
    except Exception:
        pass


def _uninstall_picker_in_frame(frame: Frame) -> None:
    try:
        if frame.is_detached():
            return
        frame.evaluate(PICKER_UNINSTALL_SCRIPT)
    except Exception:
        pass
