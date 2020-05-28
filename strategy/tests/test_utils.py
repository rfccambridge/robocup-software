# pylint: disable=import-error
from ..utils import Utils
import numpy as np


def test_tests():
    assert True


def test_perpendicular():
    """Tests that perpendicular works correctly for [1, 0] [0, 1], and [0, 0].
    """
    utils = Utils()
    x = np.array([1, 0])
    y = np.array([0, 1])
    zero = np.array([0, 0])
    perp = utils.perpendicular
    assert (perp(x) == y).all() or (perp(x) == -y).all()
    assert (perp(y) == x).all() or (perp(y) == -x).all()
    assert (perp(zero) == zero).all()


def test_distance_from_line():
    """Tests distance_from_line in the trivial case where the point is on the line.
    Passes if the returned distance is 0.
    """
    utils = Utils()
    x = np.array([1, 1])
    y = np.array([1, 2])
    pt = np.array([1, 2])
    dist = utils.distance_from_line
    assert dist(x, y, pt) == 0.
