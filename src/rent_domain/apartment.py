"""Cross-field checks independent of the request transport and model."""

from collections.abc import Mapping
from numbers import Real


class ApartmentRelationshipError(ValueError):
    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field


def validate_apartment_relationships(apartment: Mapping[str, object]) -> None:
    """Compare supplied numeric fields and require a complete coordinate pair."""
    for field, limit_field in (("floor", "total_floors"), ("kitchen_area", "area")):
        value, limit = apartment.get(field), apartment.get(limit_field)
        if isinstance(value, Real) and isinstance(limit, Real) and value > limit:
            raise ApartmentRelationshipError(
                field, f"{field} must be less than or equal to {limit_field}"
            )

    lat_missing = apartment.get("lat") is None
    lon_missing = apartment.get("lon") is None
    if lat_missing != lon_missing:
        field = "lat" if lat_missing else "lon"
        raise ApartmentRelationshipError(field, "lat and lon must be supplied together")
