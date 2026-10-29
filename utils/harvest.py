"""Unit conversions for farmer-reported harvest outcomes."""
import math

AREA_TO_HECTARES = {
    "ha": 1.0,
    "m2": 0.0001,
    "acre": 0.40468564224,
}

QUANTITY_TO_KILOGRAMS = {
    "kg": 1.0,
    "g": 0.001,
    "t": 1000.0,
    "lb": 0.45359237,
}


def yield_kg_per_hectare(area: float | None, area_unit: str | None,
                         quantity: float | None, quantity_unit: str | None) -> float | None:
    if (area is None or quantity is None or not math.isfinite(area) or not math.isfinite(quantity)
            or area <= 0 or quantity <= 0):
        return None
    area_factor = AREA_TO_HECTARES.get(area_unit or "")
    quantity_factor = QUANTITY_TO_KILOGRAMS.get(quantity_unit or "")
    if area_factor is None or quantity_factor is None:
        return None
    return round(quantity * quantity_factor / (area * area_factor), 2)


def yield_calculation(area: float | None, area_unit: str | None,
                      quantity: float | None, quantity_unit: str | None) -> str | None:
    value = yield_kg_per_hectare(area, area_unit, quantity, quantity_unit)
    if value is None:
        return None
    area_factor = AREA_TO_HECTARES[area_unit]
    quantity_factor = QUANTITY_TO_KILOGRAMS[quantity_unit]
    return (
        f"({quantity:g} {quantity_unit} x {quantity_factor:g} kg/{quantity_unit}) "
        f"/ ({area:g} {area_unit} x {area_factor:g} ha/{area_unit}) "
        f"= {value:g} kg/ha"
    )
