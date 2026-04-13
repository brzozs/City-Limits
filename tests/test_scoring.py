import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from main import get_grade

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
