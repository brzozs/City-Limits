import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.patch_pygbag_html import FALLBACK_BROWSERFS_SRC, patch_pygbag_html


def test_patch_pygbag_html_updates_background_and_aspect_ratio():
    raw_html = """
platform.document.body.style.background = "#7f7f7f"
config = {
    fb_ar   :  1.77,
    fb_width : "800",
    fb_height : "600"
}
body {
    background-color:powderblue;
}
"""

    patched = patch_pygbag_html(raw_html, width=800, height=600)

    assert '#161616' in patched
    assert '1.3333333333333333' in patched
    assert 'Rotate your phone for a larger view.' in patched
    assert 'browserfs.min.js' in patched


def test_patch_pygbag_html_is_idempotent():
    raw_html = """
platform.document.body.style.background = "#7f7f7f"
config = {
    fb_ar   :  1.77,
    fb_width : "800",
    fb_height : "600"
}
body {
    background-color:powderblue;
}
"""

    once = patch_pygbag_html(raw_html, width=800, height=600)
    twice = patch_pygbag_html(once, width=800, height=600)

    assert once == twice


def test_patch_pygbag_html_replaces_broken_browserfs_url():
    raw_html = """
<html lang="en-us"><script src="https://pygame-web.github.io/cdn/0.9.3/pythons.js" type=module id="site"></script>
<body>
    <script src="https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js"></script>
</body>
</html>
"""

    patched = patch_pygbag_html(raw_html, width=800, height=600)

    assert 'https://pygame-web.github.io/cdn/0.9.3//browserfs.min.js' not in patched
    assert patched.count("browserfs.min.js") == 1
    assert FALLBACK_BROWSERFS_SRC in patched
