import os, sys
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import pygame
pygame.init()

from intersection import Intersection, IntersectionType

ALL_ARMS = frozenset({'N', 'S', 'E', 'W'})


def test_four_arm_types_return_all_arms():
    for t in (IntersectionType.FOUR_WAY, IntersectionType.ROUNDABOUT,
              IntersectionType.CLOVERLEAF, IntersectionType.DIAMOND):
        i = Intersection(0, 0, 100, 100, intersection_type=t)
        assert i.get_arms() == ALL_ARMS, f"{t} should have all 4 arms"


def test_three_arm_type_rotation_0_missing_south():
    for t in (IntersectionType.T_INTERSECTION, IntersectionType.TRUMPET,
              IntersectionType.Y_INTERSECTION):
        i = Intersection(0, 0, 100, 100, intersection_type=t)
        assert i.get_arms() == frozenset({'N', 'E', 'W'}), f"{t} rot 0 should miss S"


def test_three_arm_type_rotation_cycles_missing_arm():
    i = Intersection(0, 0, 100, 100, intersection_type=IntersectionType.T_INTERSECTION)
    assert 'S' not in i.get_arms()
    i.rotate()
    assert 'W' not in i.get_arms()
    i.rotate()
    assert 'N' not in i.get_arms()
    i.rotate()
    assert 'E' not in i.get_arms()
    i.rotate()
    assert 'S' not in i.get_arms()


def test_four_arm_rotate_does_nothing():
    i = Intersection(0, 0, 100, 100, intersection_type=IntersectionType.ROUNDABOUT)
    before = i.get_arms()
    i.rotate()
    assert i.get_arms() == before


def test_default_type_is_four_way():
    i = Intersection(0, 0, 100, 100)
    assert i.get_arms() == ALL_ARMS


def test_partial_cloverleaf_is_three_arm():
    """PARTIAL_CLOVERLEAF should have 3 arms (rotation-dependent), not all 4."""
    i = Intersection(0, 0, 100, 100, intersection_type=IntersectionType.PARTIAL_CLOVERLEAF)
    assert len(i.get_arms()) == 3, "PARTIAL_CLOVERLEAF should have exactly 3 arms"
    assert 'S' not in i.get_arms(), "rotation 0 should be missing S"
    i.rotate()
    assert 'W' not in i.get_arms(), "rotation 1 should be missing W"
