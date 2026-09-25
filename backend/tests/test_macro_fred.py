from app.providers.macro_fred import change_points, transform
from datetime import date


def test_yoy_transform():
    # 13 monthly values, newest first, flat except last point +10%
    values = [110] + [100] * 12
    actual, prev = transform(values, "yoy", 12)
    assert round(actual, 1) == 10.0


def test_diff_transform():
    values = [160000, 159800, 159650]
    actual, prev = transform(values, "diff", 1)
    assert actual == 200
    assert prev == 150


def test_level_transform_passthrough():
    actual, prev = transform([4.0, 4.1, 4.2], "level", 1)
    assert actual == 4.0 and prev == 4.1


def test_change_points_collapses_flat_runs():
    obs = [(date(2026, 1, 1), 5.0), (date(2026, 2, 1), 5.0), (date(2026, 3, 1), 5.25), (date(2026, 4, 1), 5.25)]
    pts = change_points(obs)
    assert pts == [(date(2026, 1, 1), 5.0), (date(2026, 3, 1), 5.25)]
