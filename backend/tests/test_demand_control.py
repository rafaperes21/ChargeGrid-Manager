from decimal import Decimal

from app.services.demand_control import allocate_power

D = Decimal


def test_everything_fits_keeps_requested():
    caps = allocate_power({"a": D("11"), "b": D("7.4")}, D("40"))
    assert caps == {"a": D("11"), "b": D("7.4")}


def test_over_limit_reduces_proportionally():
    caps = allocate_power({c: D("11") for c in "abcd"}, D("40"))
    assert all(cap == D("10.000") for cap in caps.values())
    assert sum(caps.values()) <= D("40")


def test_reduction_keeps_proportions_between_chargers():
    caps = allocate_power({"grande": D("22"), "pequeno": D("11")}, D("30"))
    assert caps["grande"] == D("20.000")
    assert caps["pequeno"] == D("10.000")


def test_rounding_never_exceeds_available():
    caps = allocate_power({c: D("11") for c in "abc"}, D("10"))
    assert sum(caps.values()) <= D("10")


def test_zero_or_negative_available_blocks_all():
    assert allocate_power({"a": D("11")}, D("0")) == {"a": D("0.000")}
    assert allocate_power({"a": D("11")}, D("-5")) == {"a": D("0.000")}


def test_empty_request():
    assert allocate_power({}, D("40")) == {}
