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

  document.addEventListener('mouseover', (event) => {
    rememberHoverTarget(event.target);
  }, true);

  document.addEventListener('pointerdown', (event) => {
    const el = event.target.closest(
      'a,button,input,select,textarea,label,[role="button"],[role="link"],[type="submit"],[onclick]'
    ) || event.target;
    if (!shouldRecordClick(el)) return;

    const checkbox = checkboxInputFor(el);
    if (!checkbox || checkbox.type !== 'checkbox') return;

    const selector = buildCheckboxSelector(checkbox) || buildSelector(checkbox);
    if (!selector) return;
    const now = Date.now();
    const action = checkbox.checked ? 'uncheck' : 'check';
    const dedupeKey = `${action}::${selector}`;
    if (dedupeKey === lastToggle.key && now - lastToggle.at < 600) return;
    lastToggle = { key: dedupeKey, at: now };
    send({
      action,
      selector,
      text: checkboxLabelText(checkbox).slice(0, 120),
    });
  }, true);

  document.addEventListener('click', (event) => {
    const canvas = canvasFor(event.target);
    if (canvas) {
      const selector = buildCanvasSelector(canvas);
      if (!selector) return;
      const now = Date.now();
      const dedupeKey = `draw_signature::${selector}`;
      if (dedupeKey === lastSignature.key && now - lastSignature.at < 2000) return;
      lastSignature = { key: dedupeKey, at: now };
      send({
        action: 'draw_signature',
        selector,
        text: signatureContextText(canvas).slice(0, 120),
      });
      return;
    }

    const el = event.target.closest(
      'a,button,input,select,textarea,label,[role="button"],[role="link"],[role="menuitem"],[role="tab"],[type="submit"],[onclick]'
    ) || event.target;
    if (!shouldRecordClick(el)) return;

    const checkbox = checkboxInputFor(el);
    if (checkbox && checkbox.type === 'checkbox') return;

    if (isTextInput(el)) return;

    const clickRoot = clickableAncestor(event.target) || el;
    const selector = buildSelector(event.target);
    if (!selector) return;
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
    };
    if (hover) {
      payload.hoverSelector = hover.selector;
      payload.hoverText = hover.text;
    }
    send(payload);
  }, true);

  let inputTimer = null;
  function recordFill(el) {
    const selector = buildInputSelector(el) || buildSelector(el);
    if (!selector) return;
    send({
      action: 'fill',
      selector,
      value: el.value,
      inputType: el.type || 'text',
      text: fieldCaptionText(el).slice(0, 120) || fieldLabelText(el).slice(0, 120),
    });
  }

  document.addEventListener('input', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || !['INPUT', 'TEXTAREA'].includes(el.tagName)) return;
    if (el.type === 'checkbox' || el.type === 'radio') return;
    clearTimeout(inputTimer);
    inputTimer = setTimeout(() => recordFill(el), 400);
  }, true);

  document.addEventListener('change', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || !['INPUT', 'TEXTAREA'].includes(el.tagName)) return;
    if (el.type === 'checkbox' || el.type === 'radio') return;
    clearTimeout(inputTimer);
    recordFill(el);
  }, true);

  document.addEventListener('change', (event) => {
    if (window.__shopRecorderNavOnlyMode) return;
    const el = event.target;
    if (!el || el.tagName !== 'SELECT') return;
    const selector = buildSelector(el);
    if (!selector) return;
    send({
      action: 'select',
      selector,
      value: el.value,
      label: el.options[el.selectedIndex]?.text || ''
    });
  }, true);
})();
"""
)
