from __future__ import annotations

import argparse
import re
from pathlib import Path


ORIENTATION_HINT_TEXT = "Rotate your phone for a larger view."
ORIENTATION_HINT_CSS = """
        #orientation-hint {
            position: fixed;
            left: 50%;
            bottom: 16px;
            transform: translateX(-50%);
            padding: 10px 14px;
            border-radius: 999px;
            background: rgba(12, 12, 12, 0.82);
            color: #f5f5f5;
            font: 600 14px/1.2 Arial, sans-serif;
            letter-spacing: 0.01em;
            z-index: 30;
            display: none;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
        }
"""
ORIENTATION_HINT_HTML = f'\n    <div id="orientation-hint">{ORIENTATION_HINT_TEXT}</div>\n'
ORIENTATION_HINT_SCRIPT = """
    <script type="application/javascript">
    function update_orientation_hint() {
        const hint = document.getElementById("orientation-hint");
        if (!hint) {
            return;
        }
        const portrait = window.innerHeight > window.innerWidth;
        hint.style.display = portrait ? "block" : "none";
    }

    window.addEventListener("resize", update_orientation_hint);
    window.addEventListener("orientationchange", update_orientation_hint);
    setTimeout(update_orientation_hint, 0);
    </script>
"""
FALLBACK_BROWSERFS_SRC = "https://cdn.jsdelivr.net/npm/browserfs@1.4.3/dist/browserfs.min.js"
BROWSERFS_SCRIPT_RE = re.compile(r'<script src="[^"]*browserfs(?:\.min)?\.js"></script>')


def patch_pygbag_html(raw_html: str, width: int, height: int) -> str:
    """Apply small mobile-focused fixes to a generated pygbag index.html."""
    aspect_ratio = width / height
    html = raw_html

    html = BROWSERFS_SCRIPT_RE.sub("", html)
    browserfs_tag = f'<script src="{FALLBACK_BROWSERFS_SRC}"></script>'
    if browserfs_tag not in html:
        if "<html" in html:
            html = re.sub(r"(<html[^>]*>)", r"\1" + browserfs_tag, html, count=1)
        else:
            html = f"{browserfs_tag}\n{html.lstrip('\n')}"

    html = html.replace(
        'platform.document.body.style.background = "#7f7f7f"',
        'platform.document.body.style.background = "#161616"',
    )
    html = html.replace(
        "background-color:powderblue;",
        "background-color:#161616;\n            color: #f5f5f5;\n            min-height: 100vh;\n            overflow: hidden;\n            touch-action: manipulation;",
    )
    html = re.sub(
        r"fb_ar\s*:\s*[^,]+,",
        f"fb_ar   :  {aspect_ratio},",
        html,
        count=1,
    )

    if "#orientation-hint" not in html:
        html = html.replace("</style>", f"{ORIENTATION_HINT_CSS}\n    </style>", 1)

    if 'id="orientation-hint"' not in html:
        if "</body>" in html:
            html = html.replace("</body>", f"{ORIENTATION_HINT_HTML}</body>", 1)
        else:
            html = f"{html.rstrip()}\n{ORIENTATION_HINT_HTML}"

    if "update_orientation_hint" not in html:
        if "</body>" in html:
            html = html.replace("</body>", f"{ORIENTATION_HINT_SCRIPT}\n</body>", 1)
        else:
            html = f"{html.rstrip()}\n{ORIENTATION_HINT_SCRIPT}\n"

    return html


def patch_file(path: Path, width: int, height: int) -> None:
    raw_html = path.read_text(encoding="utf-8")
    patched = patch_pygbag_html(raw_html, width=width, height=height)
    if patched != raw_html:
        path.write_text(patched, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Patch a pygbag-generated HTML shell for mobile play.")
    parser.add_argument("html_path", type=Path)
    parser.add_argument("--width", type=int, default=800)
    parser.add_argument("--height", type=int, default=600)
    args = parser.parse_args()
    patch_file(args.html_path, width=args.width, height=args.height)


if __name__ == "__main__":
    main()
