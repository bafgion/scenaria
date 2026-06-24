"""Element highlight overlay for playback (T8a / T8b)."""

from __future__ import annotations

from playwright.sync_api import Page

HIGHLIGHT_SCRIPT = """
(selector) => {
  const prev = document.getElementById('__shopRecorderHighlight');
  if (prev) prev.remove();
  const el = document.querySelector(selector);
  if (!el) return false;
  const rect = el.getBoundingClientRect();
  const box = document.createElement('div');
  box.id = '__shopRecorderHighlight';
  box.style.cssText = [
    'position:fixed',
    'pointer-events:none',
    'z-index:2147483646',
    `left:${rect.left}px`,
    `top:${rect.top}px`,
    `width:${rect.width}px`,
    `height:${rect.height}px`,
    'border:3px solid #ff9800',
    'background:rgba(255,152,0,0.15)',
    'box-shadow:0 0 0 2px rgba(255,152,0,0.4)',
    'border-radius:4px',
    'transition:all 0.15s ease',
  ].join(';');
  document.body.appendChild(box);
  el.scrollIntoView({ block: 'center', inline: 'center', behavior: 'smooth' });
  return true;
}
"""

REMOVE_HIGHLIGHT_SCRIPT = """
() => {
  const prev = document.getElementById('__shopRecorderHighlight');
  if (prev) prev.remove();
}
"""

HIGHLIGHT_CLEANUP_INIT_SCRIPT = """
(() => {
  if (window.__shopHighlightCleanup) return;
  window.__shopHighlightCleanup = true;
  const remove = () => {
    document.getElementById('__shopRecorderHighlight')?.remove();
  };
  window.addEventListener('popstate', remove);
  window.addEventListener('hashchange', remove);
  for (const method of ['pushState', 'replaceState']) {
    const original = history[method];
    history[method] = function(...args) {
      remove();
      return original.apply(this, args);
    };
  }
  document.addEventListener('click', (event) => {
    const link = event.target.closest('a[href]');
    if (!link) return;
    const target = (link.getAttribute('target') || '_self').toLowerCase();
    if (target === '_self' || target === '') remove();
  }, true);
})();
"""

_highlight_cleanup_contexts: set[int] = set()
_highlight_cleanup_pages: set[int] = set()


def setup_highlight_cleanup(page: Page) -> None:
    context_id = id(page.context)
    if context_id not in _highlight_cleanup_contexts:
        try:
            page.context.add_init_script(HIGHLIGHT_CLEANUP_INIT_SCRIPT)
            _highlight_cleanup_contexts.add(context_id)
        except Exception:
            pass

    page_id = id(page)
    if page_id in _highlight_cleanup_pages:
        return

    try:
        page.evaluate(HIGHLIGHT_CLEANUP_INIT_SCRIPT)
    except Exception:
        pass

    def on_nav(frame) -> None:
        if frame == page.main_frame:
            remove_highlight(page)

    page.on("framenavigated", on_nav)
    _highlight_cleanup_pages.add(page_id)


def reset_highlight_cleanup_state() -> None:
    _highlight_cleanup_contexts.clear()
    _highlight_cleanup_pages.clear()


def highlight_selector(page: Page, selector: str) -> bool:
    if not selector:
        return False
    try:
        return bool(page.evaluate(HIGHLIGHT_SCRIPT, selector))
    except Exception:
        return False


def _maybe_highlight(page: Page, selector: str, *, enabled: bool, pause_ms: int = 200) -> None:
    if not enabled or not selector:
        return
    if highlight_selector(page, selector):
        page.wait_for_timeout(pause_ms)


def remove_highlight(page: Page) -> None:
    try:
        page.evaluate(REMOVE_HIGHLIGHT_SCRIPT)
    except Exception:
        pass
