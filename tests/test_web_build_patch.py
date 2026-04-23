import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.patch_pygbag_html import patch_pygbag_html


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
