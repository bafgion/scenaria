from app.selector_heuristics import SELECTOR_HEURISTICS_JS

RECORDER_INSTALLED_CHECK = "window.__shopRecorderInstalled === true"

RECORDER_INIT_SCRIPT = (
    """
(() => {
  if (window.__shopRecorderInstalled) return;
  window.__shopRecorderInstalled = true;
"""
    + SELECTOR_HEURISTICS_JS
    + """
  function send(step) {
    const record = window.recordStep;
    if (typeof record !== 'function') return;
    Promise.resolve(record(step)).catch(() => {});
  }

  function isSubmenuContainer(node) {
    if (!node || node.nodeType !== 1) return false;
    if (node.matches('ul, ol, nav, [role="menu"], [class*="sub"], [class*="drop"], [class*="mega"], [class*="menu"]')) {
      return true;
    }
    return node.children.length > 2 && !!node.querySelector('a, button');
  }

  function findMenuHoverTrigger(el) {
    if (!el || el.nodeType !== 1) return null;

    let item = el.closest('li');
    while (item) {
      const trigger = item.querySelector(':scope > a, :scope > button, :scope > [role="button"]');
      if (trigger) {
        for (const child of Array.from(item.children)) {
          if (child === trigger) continue;
          if (isSubmenuContainer(child) && child.contains(el) && trigger !== el) {
            const selector = buildSelector(trigger);
            if (!selector) return null;
            return {
              selector,
              text: (trigger.innerText || trigger.textContent || '').trim().slice(0, 120),
            };
          }
        }
      }
      item = item.parentElement ? item.parentElement.closest('li') : null;
    }

    let node = el.parentElement;
    for (let depth = 0; node && depth < 8; depth++) {
      const directTriggers = node.querySelectorAll(':scope > a, :scope > button, :scope > [role="button"]');
      for (const trigger of directTriggers) {
        if (trigger === el || trigger.contains(el)) continue;
        for (const child of node.children) {
          if (child === trigger) continue;
          if (isSubmenuContainer(child) && child.contains(el)) {
            const selector = buildSelector(trigger);
            if (selector) {
              return {
                selector,
                text: (trigger.innerText || trigger.textContent || '').trim().slice(0, 120),
              };
            }
          }
        }
      }
      node = node.parentElement;
    }

    const header = el.closest('header, nav');
    if (header) {
      const triggers = header.querySelectorAll('a, button');
      for (const trigger of triggers) {
        let sibling = trigger.nextElementSibling;
        while (sibling) {
          if (isSubmenuContainer(sibling) && sibling.contains(el)) {
            const selector = buildSelector(trigger);
            if (selector) {
              return {
                selector,
                text: (trigger.innerText || trigger.textContent || '').trim().slice(0, 120),
              };
            }
          }
          sibling = sibling.nextElementSibling;
        }
      }
    }

    return null;
  }

  let lastClick = { selector: '', at: 0 };
  let lastToggle = { key: '', at: 0 };
  let lastSignature = { key: '', at: 0 };
  let lastPress = { key: '', at: 0 };

  const RECORDED_KEYS = new Set(['Enter', 'Tab', 'Escape']);

  function isImportantElement(el) {
    if (!el || el.nodeType !== 1) return false;
    const tag = el.tagName;
    if (['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA', 'LABEL'].includes(tag)) return true;
    if (el.getAttribute('role') === 'button' || el.getAttribute('role') === 'link') return true;
    if (el.getAttribute('type') === 'submit') return true;
    if (el.getAttribute('onclick')) return true;
    if (el.getAttribute('data-testid')) return true;
    if (el.id) return true;
  }

  function shouldRecordClick(el) {
    if (window.__shopRecorderNavOnlyMode) {
      if (el.tagName === 'A' && el.getAttribute('href')) return true;
      return false;
    }
    if (!window.__shopRecorderFilterMode) return true;
    if (isImportantElement(el)) return true;
    const text = (el.innerText || '').trim().toLowerCase();
    const cookieWords = ['cookie', 'принять', 'accept', 'соглас', 'ok', 'понятно', 'закрыть'];
    if (cookieWords.some((w) => text.includes(w))) return true;
    return false;
  }

  let lastHoverTrigger = null;
  let hoverRecordTimer = null;
  let lastRecordedHover = { selector: '', at: 0 };

  function hoverRecordMinMs() {
    const value = Number(window.__shopRecorderHoverMinMs);
    return Number.isFinite(value) && value >= 100 ? value : 300;
  }

  function isHoverRecordTarget(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.matches('a[href], button, [role="button"], [role="menuitem"], [role="tab"], [role="link"]')) {
      return true;
    }
    const nav = el.closest('nav, header');
    return !!nav && !!el.closest('a, button, [role="button"], [role="menuitem"]');
  }

  function scheduleHoverRecord(el) {
    if (!window.__shopRecorderHoverMode || window.__shopRecorderNavOnlyMode) return;
    if (!isHoverRecordTarget(el) || !shouldRecordClick(el)) return;
    clearTimeout(hoverRecordTimer);
    const target = el.closest('a, button, [role="button"], [role="menuitem"], [role="tab"], [role="link"]') || el;
    hoverRecordTimer = setTimeout(() => {
      const selector = buildSelector(target);
      if (!selector) return;
      const now = Date.now();
      if (selector === lastRecordedHover.selector && now - lastRecordedHover.at < 800) return;
      lastRecordedHover = { selector, at: now };
      send(enrichStep({
        action: 'hover',
        selector,
        text: visibleText(target).slice(0, 120),
      }, target));
    }, hoverRecordMinMs());
  }

  document.addEventListener('mouseover', (event) => {
    rememberHoverTarget(event.target);
    const el = event.target;
    if (el && el.nodeType === 1) {
      scheduleHoverRecord(el);
    }
  }, true);

  function sameNavContext(a, b) {
    const navA = a?.closest('header, nav');
    const navB = b?.closest('header, nav');
    return !!navA && navA === navB;
  }

  function rememberHoverTarget(el) {
    if (!el || el.nodeType !== 1) return;
    const trigger = el.closest('a,button,[role="button"]');
    if (!trigger) return;
    const selector = buildSelector(trigger);
    if (!selector) return;
    const text = (trigger.innerText || trigger.textContent || '').trim().slice(0, 120);
    lastHoverTrigger = {
      element: trigger,
      selector,
      text,
      at: Date.now(),
    };
  }

  document.addEventListener('pointerdown', (event) => {
    const el = event.target.closest(
      'a,button,input,select,textarea,label,[role="button"],[role="link"],[type="submit"],[onclick]'
    ) || event.target;
    if (!shouldRecordClick(el)) return;

    const checkbox = checkboxInputFor(el);
    if (checkbox && checkbox.type === 'checkbox') {
      const selector = buildCheckboxSelector(checkbox) || buildSelector(checkbox);
      if (!selector) return;
      const now = Date.now();
      const action = checkbox.checked ? 'uncheck' : 'check';
      const dedupeKey = `${action}::${selector}`;
      if (dedupeKey === lastToggle.key && now - lastToggle.at < 600) return;
      lastToggle = { key: dedupeKey, at: now };
      send(enrichStep({
        action,
        selector,
        text: checkboxLabelText(checkbox).slice(0, 120),
      }, checkbox));
      return;
    }
    if (checkbox && checkbox.type === 'radio') {
      const selector = buildCheckboxSelector(checkbox) || buildSelector(checkbox);
      if (!selector) return;
      const now = Date.now();
      const dedupeKey = `check::${selector}`;
      if (dedupeKey === lastToggle.key && now - lastToggle.at < 600) return;
      lastToggle = { key: dedupeKey, at: now };
      send(enrichStep({
        action: 'check',
        selector,
        text: checkboxLabelText(checkbox).slice(0, 120),
      }, checkbox));
    }
  }, true);

  document.addEventListener('dblclick', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target.closest(
      'a,button,input,select,textarea,label,[role="button"],[role="link"],[role="menuitem"],[type="submit"],[onclick]'
    ) || event.target;
    if (!shouldRecordClick(el)) return;
    if (isTextInput(el)) return;
    const selector = buildSelector(event.target);
    if (!selector) return;
    const now = Date.now();
    lastClick = { selector: '', at: now };
    send(enrichStep({
      action: 'double_click',
      selector,
      text: visibleText(el).slice(0, 120),
    }, el));
  }, true);

  function isInViewport(el) {
    if (!el || !el.getBoundingClientRect) return true;
    const rect = el.getBoundingClientRect();
    const height = window.innerHeight || document.documentElement.clientHeight;
    const width = window.innerWidth || document.documentElement.clientWidth;
    return rect.bottom > 0 && rect.right > 0 && rect.top < height && rect.left < width;
  }

  function maybeRecordScrollTo(el, selector) {
    if (!window.__shopRecorderScrollBeforeClick || !selector || !el) return;
    if (isInViewport(el)) return;
    send(enrichStep({ action: 'scroll_to', selector }, el));
  }

  document.addEventListener('click', (event) => {
    const canvas = canvasFor(event.target);
    if (canvas) {
      const selector = buildCanvasSelector(canvas);
      if (!selector) return;
      const now = Date.now();
      const dedupeKey = `draw_signature::${selector}`;
      if (dedupeKey === lastSignature.key && now - lastSignature.at < 2000) return;
      lastSignature = { key: dedupeKey, at: now };
      send(enrichStep({
        action: 'draw_signature',
        selector,
        text: signatureContextText(canvas).slice(0, 120),
      }, canvas));
      return;
    }

    const el = event.target.closest(
      'a,button,input,select,textarea,label,[role="button"],[role="link"],[role="menuitem"],[role="tab"],[type="submit"],[onclick]'
    ) || event.target;
    if (!shouldRecordClick(el)) return;

    const checkbox = checkboxInputFor(el);
    if (checkbox && (checkbox.type === 'checkbox' || checkbox.type === 'radio')) return;

    if (isTextInput(el)) return;

    const clickRoot = clickableAncestor(event.target) || el;
    const selector = buildSelector(event.target);
    if (!selector) return;
    maybeRecordScrollTo(clickRoot, selector);
    const now = Date.now();
    if (selector === lastClick.selector && now - lastClick.at < 600) return;
    lastClick = { selector, at: now };
    let hover = findMenuHoverTrigger(el);
    if (!hover && lastHoverTrigger && now - lastHoverTrigger.at < 12000) {
      if (
        lastHoverTrigger.selector !== selector &&
        sameNavContext(el, lastHoverTrigger.element) &&
        !lastHoverTrigger.element.contains(el)
      ) {
        hover = {
          selector: lastHoverTrigger.selector,
          text: lastHoverTrigger.text,
        };
      }
    }
    const payload = {
      action: 'click',
      selector,
      text: visibleText(clickRoot).slice(0, 120),
      contextText: clickContextCaption(clickRoot).slice(0, 120),
    };
    if (hover) {
      payload.hoverSelector = hover.selector;
      payload.hoverText = hover.text;
    }
    send(enrichStep(payload, clickRoot, { contextText: payload.contextText }));
  }, true);

  let inputTimer = null;
  function recordFill(el) {
    const selector = buildInputSelector(el) || buildSelector(el);
    if (!selector) return;
    send(enrichStep({
      action: 'fill',
      selector,
      value: el.value,
      inputType: el.type || 'text',
      text: fieldCaptionText(el).slice(0, 120) || fieldLabelText(el).slice(0, 120),
    }, el));
  }

  document.addEventListener('input', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || !['INPUT', 'TEXTAREA'].includes(el.tagName)) return;
    if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'file') return;
    clearTimeout(inputTimer);
    inputTimer = setTimeout(() => recordFill(el), 400);
  }, true);

  document.addEventListener('change', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || el.tagName !== 'INPUT' || el.type !== 'file') return;
    const selector = buildInputSelector(el) || buildSelector(el);
    if (!selector) return;
    const fileName = el.files && el.files.length ? el.files[0].name : '';
    send(enrichStep({
      action: 'upload',
      selector,
      path: fileName ? `<${fileName}>` : '<файл>',
      text: fieldCaptionText(el).slice(0, 120) || fieldLabelText(el).slice(0, 120),
    }, el));
  }, true);

  document.addEventListener('keydown', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    if (!RECORDED_KEYS.has(event.key)) return;
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    const el = event.target;
    if (!el || el.nodeType !== 1) return;
    if (!isTextInput(el) && !el.isContentEditable) return;
    const selector = buildInputSelector(el) || buildSelector(el);
    if (!selector) return;
    const now = Date.now();
    const dedupeKey = `${event.key}::${selector}`;
    if (dedupeKey === lastPress.key && now - lastPress.at < 600) return;
    lastPress = { key: dedupeKey, at: now };
    send(enrichStep({
      action: 'press',
      key: event.key,
      selector,
      text: fieldCaptionText(el).slice(0, 120) || fieldLabelText(el).slice(0, 120),
    }, el));
  }, true);

  document.addEventListener('change', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || !['INPUT', 'TEXTAREA'].includes(el.tagName)) return;
    if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'file') return;
    clearTimeout(inputTimer);
    recordFill(el);
  }, true);

  document.addEventListener('change', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || el.tagName !== 'SELECT') return;
    const selector = buildSelector(el);
    if (!selector) return;
    send(enrichStep({
      action: 'select',
      selector,
      value: el.value,
      label: el.options[el.selectedIndex]?.text || ''
    }, el));
  }, true);
})();
"""
)
