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
    find_grid_cell_at_pos,
    get_browser_control_rects,
    get_touch_action_states,
    get_touch_palette_overlay_slot_rects,
    get_touch_toolbar_button_rects,
    is_duplicate_pointer_down,
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


def test_duplicate_pointer_down_detects_matching_mouse_and_touch_taps():
    previous_down = {
        "pointer": "mouse",
        "pos": (400, 300),
        "time_ms": 1000,
    }
    normalized = {
        "kind": "down",
        "pos": (404, 296),
        "button": 1,
        "pointer": "touch",
    }

    assert is_duplicate_pointer_down(normalized, previous_down, 1200) is True


def test_duplicate_pointer_down_ignores_far_or_stale_events():
    previous_down = {
        "pointer": "mouse",
        "pos": (400, 300),
        "time_ms": 1000,
    }

    assert is_duplicate_pointer_down(
        {"kind": "down", "pos": (460, 300), "button": 1, "pointer": "touch"},
        previous_down,
        1100,
    ) is False
    assert is_duplicate_pointer_down(
        {"kind": "down", "pos": (404, 296), "button": 1, "pointer": "touch"},
        previous_down,
        1500,
    ) is False
    assert is_duplicate_pointer_down(
        {"kind": "down", "pos": (404, 296), "button": 1, "pointer": "mouse"},
        previous_down,
        1100,
    ) is False


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


def test_browser_controls_use_larger_touch_targets():
    controls = get_browser_control_rects(WINDOW_WIDTH, WINDOW_HEIGHT)

    assert controls["back"].width >= 120
    assert controls["back"].height >= 52
    assert controls["start"].width >= 132
    assert controls["start"].height >= 56
    assert controls["pause"].width >= 120
    assert controls["pause"].height >= 52
    assert controls["palette_toggle"].width >= 180
    assert controls["palette_toggle"].height >= 56

    names = list(controls)
    for name, rect in controls.items():
        assert rect.left >= 0, name
        assert rect.right <= WINDOW_WIDTH, name
        assert rect.top >= 0, name
        assert rect.bottom <= WINDOW_HEIGHT, name

    for index, name in enumerate(names):
        for other_name in names[index + 1:]:
            assert not controls[name].colliderect(controls[other_name]), (name, other_name)


def test_touch_palette_overlay_slots_are_large_and_non_overlapping():
    slots = get_touch_palette_overlay_slot_rects(WINDOW_WIDTH, WINDOW_HEIGHT, slot_count=8)

    assert len(slots) == 8

    for index, rect in enumerate(slots):
        assert rect.width >= 240, index
        assert rect.height >= 64, index
        assert rect.left >= 0, index
        assert rect.right <= WINDOW_WIDTH, index
        assert rect.top >= 0, index
        assert rect.bottom <= WINDOW_HEIGHT, index

    for index, rect in enumerate(slots):
        for other_index in range(index + 1, len(slots)):
            assert not rect.colliderect(slots[other_index]), (index, other_index)


def test_find_grid_cell_at_pos_maps_taps_to_cells():
    assert find_grid_cell_at_pos((150, 175), 100, 100, 150, 3, 3) == (0, 0)
    assert find_grid_cell_at_pos((399, 349), 100, 100, 150, 3, 3) == (1, 1)
    assert find_grid_cell_at_pos((549, 549), 100, 100, 150, 3, 3) == (2, 2)
    assert find_grid_cell_at_pos((99, 100), 100, 100, 150, 3, 3) is None
    assert find_grid_cell_at_pos((550, 550), 100, 100, 150, 3, 3) is None
