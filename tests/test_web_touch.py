import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pygame

pygame.init()

from main import (
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    get_touch_action_states,
    get_touch_toolbar_button_rects,
    is_browser_runtime,
    normalize_pointer_event,
)


def test_is_browser_runtime_only_for_emscripten():
    assert is_browser_runtime("emscripten") is True
    assert is_browser_runtime("darwin") is False
    assert is_browser_runtime("linux") is False


def test_normalize_pointer_event_keeps_mouse_pixels():
    event = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": (123, 234), "button": 1})

    normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)

    assert normalized == {
        "kind": "down",
        "pos": (123, 234),
        "button": 1,
        "pointer": "mouse",
    }


def test_normalize_pointer_event_scales_finger_to_surface():
    event = pygame.event.Event(
        pygame.FINGERDOWN,
        {"x": 0.25, "y": 0.5, "finger_id": 7, "touch_id": 1},
    )

    normalized = normalize_pointer_event(event, WINDOW_WIDTH, WINDOW_HEIGHT)

    assert normalized == {
        "kind": "down",
        "pos": (WINDOW_WIDTH * 0.25, WINDOW_HEIGHT * 0.5),
        "button": 1,
        "pointer": "touch",
    }


def test_touch_toolbar_buttons_fit_without_overlap():
    buttons = get_touch_toolbar_button_rects(WINDOW_WIDTH, WINDOW_HEIGHT)
    names = list(buttons)

    for name, rect in buttons.items():
        assert rect.left >= 0, name
        assert rect.right <= WINDOW_WIDTH, name
        assert rect.top >= 0, name
        assert rect.bottom <= WINDOW_HEIGHT, name

    for index, name in enumerate(names):
        for other_name in names[index + 1:]:
            assert not buttons[name].colliderect(buttons[other_name]), (name, other_name)


def test_touch_actions_follow_drag_select_and_undo_state():
    assert get_touch_action_states(False, False, False) == {
        "rotate": False,
        "delete": False,
        "undo": False,
    }
    assert get_touch_action_states(True, False, False) == {
        "rotate": True,
        "delete": False,
        "undo": False,
    }
    assert get_touch_action_states(False, True, False) == {
        "rotate": True,
        "delete": True,
        "undo": False,
    }
    assert get_touch_action_states(False, True, True) == {
        "rotate": True,
        "delete": True,
        "undo": True,
    }
