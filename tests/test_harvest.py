import pytest

from utils.harvest import yield_calculation, yield_kg_per_hectare


@pytest.mark.parametrize(
    ("area", "area_unit", "quantity", "quantity_unit", "expected"),
    [
        (0.5, "ha", 200, "kg", 400),
        (10000, "m2", 500, "kg", 500),
        (1, "acre", 1, "t", 2471.05),
        (1, "ha", 1000, "g", 1),
        (1, "ha", 100, "lb", 45.36),
    ],
)
def test_harvest_yield_converts_valid_units_and_rounds(area, area_unit, quantity, quantity_unit, expected):
    assert yield_kg_per_hectare(area, area_unit, quantity, quantity_unit) == expected


@pytest.mark.parametrize(
    ("area", "area_unit", "quantity", "quantity_unit"),
    [
        (None, "ha", 20, "kg"),
        (0, "ha", 20, "kg"),
        (-1, "ha", 20, "kg"),
        (float("nan"), "ha", 20, "kg"),
        (1, "ha", float("inf"), "kg"),
        (1, "unknown", 20, "kg"),
        (1, "ha", None, "kg"),
        (1, "ha", 20, "unknown"),
    ],
)
def test_missing_or_invalid_inputs_do_not_produce_yield(area, area_unit, quantity, quantity_unit):
    assert yield_kg_per_hectare(area, area_unit, quantity, quantity_unit) is None
    assert yield_calculation(area, area_unit, quantity, quantity_unit) is None


def test_calculation_explains_unit_conversion():
    assert yield_calculation(1, "acre", 1, "t") == (
        "(1 t x 1000 kg/t) / (1 acre x 0.404686 ha/acre) = 2471.05 kg/ha"
    )
