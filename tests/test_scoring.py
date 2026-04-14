import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pytest
from main import get_grade, calculate_flow_rate

def test_grade_a():
    assert get_grade(0.80) == 'A'
    assert get_grade(1.00) == 'A'

def test_grade_b():
    assert get_grade(0.65) == 'B'
    assert get_grade(0.79) == 'B'

def test_grade_c():
    assert get_grade(0.45) == 'C'
    assert get_grade(0.64) == 'C'

def test_grade_d():
    assert get_grade(0.25) == 'D'
    assert get_grade(0.44) == 'D'

def test_grade_f():
    assert get_grade(0.0) == 'F'
    assert get_grade(0.24) == 'F'

def test_flow_rate_empty_stats():
    """No completed cars → 0.0."""
    assert calculate_flow_rate([]) == 0.0

def test_flow_rate_zero_travel_time():
    """If total actual time is 0, return 0.0 (avoid ZeroDivisionError)."""
    # path_length=100, travel_time=0, idle_time=0
    assert calculate_flow_rate([(100, 0, 0)]) == 0.0

def test_flow_rate_routing_penalty():
    """Missed routings reduce score proportionally."""
    # One perfect car delivered
    stats = [(80, 1.0, 0.0)]  # path=80px, travel=1s, idle=0 → ideal time = 80/80 = 1s → ratio=1
    full = calculate_flow_rate(stats, spawn_attempts=1, spawn_successes=1)
    half = calculate_flow_rate(stats, spawn_attempts=2, spawn_successes=1)
    assert half == pytest.approx(full * 0.5, rel=1e-3)

def test_flow_rate_all_idle():
    """All idle time collapses idle_ratio to 0 → flow_rate = 0."""
    # travel_time == idle_time
    stats = [(100, 2.0, 2.0)]
    assert calculate_flow_rate(stats) == pytest.approx(0.0, abs=1e-9)
