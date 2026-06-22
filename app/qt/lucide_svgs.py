"""Lucide icon SVG bodies (MIT) — https://lucide.dev

Inner markup only; wrapped with stroke template in icons._lucide_template().
"""

from __future__ import annotations

# Logical Scenaria icon name → Lucide SVG inner elements (24×24 viewBox).
LUCIDE_BODIES: dict[str, str] = {
    "house": (
        '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/>'
        '<path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    ),
    "explorer": (
        '<path d="M21 12h-8"/>'
        '<path d="M21 6H8"/>'
        '<path d="M21 18h-8"/>'
        '<path d="M3 6v4c0 1.1.9 2 2 2h3"/>'
        '<path d="M3 10v6c0 1.1.9 2 2 2h3"/>'
    ),
    "panel": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 15h18"/>',
    "plus": '<path d="M5 12h14"/><path d="M12 5v14"/>',
    "close": '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
    "save": (
        '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/>'
        '<path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/>'
        '<path d="M7 3v4a1 1 0 0 0 1 1h7"/>'
    ),
    "feature": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>'
    ),
    "play": '<path d="M5 5a2 2 0 0 1 3.008-1.728l11.997 6.998a2 2 0 0 1 .003 3.458l-12 7A2 2 0 0 1 5 19z"/>',
    "stop": '<rect width="16" height="16" x="4" y="4" rx="1"/>',
    "record": '<circle cx="12" cy="12" r="10"/>',
    "pause": '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    "browser": (
        '<circle cx="12" cy="12" r="10"/>'
        '<path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
        '<path d="M2 12h20"/>'
    ),
    "browser_focus": (
        '<rect x="2" y="4" width="20" height="16" rx="2"/>'
        '<path d="M10 4v4"/><path d="M2 8h20"/><path d="M6 4v0"/>'
    ),
    "validate": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "apply": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="m9 15 2 2 4-4"/>'
    ),
    "check": (
        '<path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/>'
        '<path d="m14 7 3 3"/>'
        '<path d="M5 6v4"/><path d="M19 14v4"/><path d="M10 2v2"/>'
        '<path d="M7 8H3"/><path d="M21 16h-4"/><path d="M11 3H9"/>'
    ),
    "url": (
        '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>'
        '<path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'
    ),
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 5.5 5.5a5.5 5.5 0 0 1-5.5 5.5H11"/>',
    "log": (
        '<path d="M15 12h-5"/><path d="M15 8h-5"/>'
        '<path d="M19 17V5a2 2 0 0 0-2-2H4"/>'
        '<path d="M8 21h12a2 2 0 0 0 2-2v-1a1 1 0 0 0-1-1H11a1 1 0 0 0-1 1v1a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v2a1 1 0 0 0 1 1h3"/>'
    ),
    "results": (
        '<path d="M3 3v16a2 2 0 0 0 2 2h16"/>'
        '<path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>'
    ),
    "quick_record": (
        '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13.5 11H20a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 10.5 13z"/>'
    ),
    "picker": (
        '<path d="M12.586 12.586 19 19"/>'
        '<path d="M18.5 3.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4Z"/>'
        '<path d="m8 8 1.5 1.5"/>'
    ),
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "folder_missing": (
        '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>'
        '<path d="m14.5 10.5-5 5"/><path d="m9.5 10.5 5 5"/>'
    ),
}


def lucide_template(body: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        'stroke="{stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
        f"{body}</svg>"
    )
