"""Shared in-browser selector heuristics for recorder and picker."""

SELECTOR_HEURISTICS_JS = """
  function cssEscape(value) {
    if (window.CSS && CSS.escape) return CSS.escape(value);
    return String(value).replace(/["\\\\]/g, '\\\\$&');
  }

  function visibleText(el) {
    if (!el || el.nodeType !== 1) return '';
    const clone = el.cloneNode(true);
    clone.querySelectorAll('input, textarea, select, script, style, noscript, svg').forEach((node) => {
      node.remove();
    });
    return (clone.innerText || clone.textContent || '').trim().replace(/\\s+/g, ' ');
  }

  function labelTextForControl(el) {
    if (!el || el.nodeType !== 1) return '';
    if (el.tagName === 'LABEL') {
      return visibleText(el);
    }
    const id = el.id;
    if (id) {
      const linked = el.ownerDocument.querySelector(`label[for="${cssEscape(id)}"]`);
      if (linked) {
        return visibleText(linked);
      }
    }
    const parentLabel = el.closest('label');
    if (parentLabel) {
      return visibleText(parentLabel);
    }
    return '';
  }

  function checkboxLabelText(input) {
    if (!input) return '';
    const direct = labelTextForControl(input);
    if (direct.length >= 4) return direct;

    const aria = input.getAttribute('aria-label');
    if (aria && aria.trim().length >= 4) return aria.trim();

    const labelledBy = input.getAttribute('aria-labelledby');
    if (labelledBy) {
      const chunks = labelledBy.split(/\\s+/).map((id) => {
        const node = input.ownerDocument.getElementById(id);
        return node ? visibleText(node) : '';
      }).filter(Boolean);
      if (chunks.length) {
        const joined = chunks.join(' ').trim();
        if (joined.length >= 4) return joined;
      }
    }

    let node = input.parentElement;
    for (let depth = 0; node && depth < 8; depth++) {
      if (node.tagName === 'LABEL') {
        const labelText = visibleText(node);
        if (labelText.length >= 4) return labelText;
      }
      const parts = [];
      for (const child of Array.from(node.children)) {
        if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'SVG'].includes(child.tagName)) continue;
        if (child.tagName === 'INPUT' && child !== input) continue;
        const text = visibleText(child);
        if (text.length >= 4) parts.push(text);
      }
      if (parts.length === 1) return parts[0];
      if (parts.length > 1) {
        parts.sort((a, b) => b.length - a.length);
        const best = parts[0];
        if (best.length >= 4 && best.length <= 200) return best;
      }
      node = node.parentElement;
    }
    return '';
  }

  function textSelectorSnippet(text, minLen) {
    const min = typeof minLen === 'number' ? minLen : 4;
    if (!text || text.length < min) return null;
    const snippet = text.length > 60 ? text.slice(0, 40) : text;
    if (snippet.length < min) return null;
    return `label:has-text("${snippet.replace(/"/g, '\\\\"')}")`;
  }

  function checkboxInputFor(el) {
    if (!el || el.nodeType !== 1) return null;
    if (el.tagName === 'INPUT' && (el.type === 'checkbox' || el.type === 'radio')) return el;
    if (el.tagName === 'LABEL') {
      const nested = el.querySelector('input[type="checkbox"], input[type="radio"]');
      if (nested) return nested;
      const forId = el.getAttribute('for');
      if (forId) {
        const linked = el.ownerDocument.getElementById(forId);
        if (linked && linked.tagName === 'INPUT') return linked;
      }
    }
    const parentLabel = el.closest('label');
    if (parentLabel) {
      const nested = parentLabel.querySelector('input[type="checkbox"], input[type="radio"]');
      if (nested) return nested;
    }
    return null;
  }

  function buildCheckboxSelector(input) {
    if (!input || input.tagName !== 'INPUT') return null;
    const type = input.type || 'checkbox';
    if (type !== 'checkbox' && type !== 'radio') return null;

    const testId = input.getAttribute('data-testid');
    if (testId) return `[data-testid="${cssEscape(testId)}"]`;

    if (input.id) return `#${cssEscape(input.id)}`;

    const labelText = checkboxLabelText(input);
    const textSelector = textSelectorSnippet(labelText);
    if (textSelector) return textSelector;

    const aria = input.getAttribute('aria-label');
    if (aria && aria.trim().length >= 4) {
      return `[aria-label="${cssEscape(aria.trim())}"]`;
    }

    const name = input.getAttribute('name');
    if (name) return `input[type="${type}"][name="${cssEscape(name)}"]`;

    return null;
  }

  function fieldLabelText(input) {
    return checkboxLabelText(input);
  }

  function normalizeCaption(text) {
    return String(text || '').replace(/\\s*\\*+\\s*$/g, '').trim();
  }

  function isGenericPlaceholder(placeholder) {
    if (!placeholder) return true;
    const normalized = placeholder.trim().toLowerCase().replace(/\\s+/g, '');
    const generic = [
      'дд.мм.гггг',
      'дд/мм/гггг',
      'dd.mm.yyyy',
      'mm/dd/yyyy',
      '__.__.____',
      '--.--.----',
    ];
    if (generic.includes(normalized)) return true;
    if (/^[дd_.\\-/]{4,}$/i.test(normalized)) return true;
    return false;
  }

  function fieldCaptionText(input) {
    if (!input) return '';
    const parentLabel = input.closest('label');
    if (parentLabel) {
      for (const child of Array.from(parentLabel.children)) {
        if (child.contains(input)) continue;
        if (['INPUT', 'TEXTAREA', 'SELECT', 'SCRIPT', 'STYLE'].includes(child.tagName)) continue;
        const text = normalizeCaption(visibleText(child));
        if (text.length >= 2) return text;
      }
    }

    let node = input.parentElement;
    for (let depth = 0; node && depth < 8; depth++) {
      const prev = input.previousElementSibling;
      if (prev && !prev.querySelector('input, textarea, select')) {
        const text = normalizeCaption(visibleText(prev));
        if (text.length >= 2 && text.length <= 120) return text;
      }
      for (const child of Array.from(node.children)) {
        if (child === input || child.contains(input)) continue;
        if (['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON', 'SCRIPT', 'STYLE'].includes(child.tagName)) {
          continue;
        }
        if (child.querySelector('input, textarea, select')) continue;
        const text = normalizeCaption(visibleText(child));
        if (text.length >= 2 && text.length <= 120) return text;
      }
      const parentPrev = node.previousElementSibling;
      if (parentPrev && !parentPrev.querySelector('input, textarea, select')) {
        const text = normalizeCaption(visibleText(parentPrev));
        if (text.length >= 2 && text.length <= 80) return text;
      }
      node = node.parentElement;
    }
    return normalizeCaption(fieldLabelText(input));
  }

  function buildInputSelector(el) {
    if (!el || !['INPUT', 'TEXTAREA'].includes(el.tagName)) return null;
    const tag = el.tagName.toLowerCase();
    const type = (el.type || 'text').toLowerCase();

    if (type === 'checkbox' || type === 'radio') {
      return buildCheckboxSelector(el);
    }

    const testId = el.getAttribute('data-testid');
    if (testId) return `[data-testid="${cssEscape(testId)}"]`;

    if (el.id) return `#${cssEscape(el.id)}`;

    const caption = fieldCaptionText(el);
    const textSelector = textSelectorSnippet(caption, 2) || textSelectorSnippet(fieldLabelText(el));
    if (textSelector) return textSelector;

    const placeholder = el.getAttribute('placeholder');
    if (placeholder && !isGenericPlaceholder(placeholder)) {
      return `${tag}[placeholder="${cssEscape(placeholder)}"]`;
    }

    const aria = el.getAttribute('aria-label');
    if (aria && aria.trim()) return `[aria-label="${cssEscape(aria.trim())}"]`;

    const autocomplete = el.getAttribute('autocomplete');
    if (autocomplete && tag === 'input') {
      return `input[autocomplete="${cssEscape(autocomplete)}"]`;
    }

    const name = el.getAttribute('name');
    if (name) return `${tag}[name="${cssEscape(name)}"]`;

    if (placeholder) return `${tag}[placeholder="${cssEscape(placeholder)}"]`;

    return null;
  }

  function canvasFor(el) {
    if (!el || el.nodeType !== 1) return null;
    if (el.tagName === 'CANVAS') return el;
    return el.closest('canvas');
  }

  function signatureContextText(canvas) {
    let node = canvas.parentElement;
    for (let depth = 0; node && depth < 8; depth++) {
      const text = visibleText(node);
      const lowered = text.toLowerCase();
      if (lowered.includes('подпис') || lowered.includes('signature')) {
        if (text.length <= 80) return text;
        const match = text.match(/[^\\n.]{0,50}подпис[^\\n.]{0,40}/i);
        if (match) return match[0].trim();
      }
      node = node.parentElement;
    }
    return '';
  }

  function buildCanvasSelector(canvas) {
    if (!canvas || canvas.tagName !== 'CANVAS') return null;

    const testId = canvas.getAttribute('data-testid');
    if (testId) return `[data-testid="${cssEscape(testId)}"]`;

    if (canvas.id) return `#${cssEscape(canvas.id)}`;

    const aria = canvas.getAttribute('aria-label');
    if (aria && aria.trim()) {
      return `canvas[aria-label="${cssEscape(aria.trim())}"]`;
    }

    const contextText = signatureContextText(canvas);
    if (contextText.length >= 4) {
      const snippet = contextText.length > 40 ? contextText.slice(0, 30) : contextText;
      return `div:has-text("${snippet.replace(/"/g, '\\\\"')}") canvas`;
    }

    return 'canvas';
  }

  function isTextInput(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.tagName === 'TEXTAREA') return true;
    if (el.tagName !== 'INPUT') return false;
    const type = (el.type || 'text').toLowerCase();
    return ['text', 'email', 'password', 'tel', 'search', 'url', 'number', ''].includes(type);
  }

  function buildSelector(el) {
    if (!el || el.nodeType !== 1) return null;

    const inputSelector = buildInputSelector(el);
    if (inputSelector) return inputSelector;

    const testId = el.getAttribute('data-testid');
    if (testId) return `[data-testid="${cssEscape(testId)}"]`;

    if (el.id) return `#${cssEscape(el.id)}`;

    const name = el.getAttribute('name');
    if (name && ['SELECT'].includes(el.tagName)) {
      return `${el.tagName.toLowerCase()}[name="${cssEscape(name)}"]`;
    }

    const aria = el.getAttribute('aria-label');
    if (aria) return `[aria-label="${cssEscape(aria)}"]`;

    if (el.tagName === 'LABEL') {
      const labelText = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
      if (labelText && labelText.length > 0 && labelText.length <= 80) {
        return `label:has-text("${labelText.replace(/"/g, '\\\\"')}")`;
      }
    }

    const role = el.getAttribute('role');
    const text = (el.innerText || el.textContent || '').trim().replace(/\\s+/g, ' ');
    if (role && text && text.length <= 80) {
      return `role=${role}[name="${text.replace(/"/g, '\\\\"')}"]`;
    }

    if (['A', 'BUTTON'].includes(el.tagName) && text && text.length <= 80) {
      return `${el.tagName.toLowerCase()}:has-text("${text.replace(/"/g, '\\\\"')}")`;
    }

    const parts = [];
    let node = el;
    while (node && node.nodeType === 1 && parts.length < 5) {
      let part = node.tagName.toLowerCase();
      if (node.id) {
        parts.unshift(`#${cssEscape(node.id)}`);
        break;
      }
      const parent = node.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter((c) => c.tagName === node.tagName);
        if (siblings.length > 1) {
          part += `:nth-of-type(${siblings.indexOf(node) + 1})`;
        }
      }
      parts.unshift(part);
      node = parent;
    }
    return parts.join(' > ');
  }
"""
