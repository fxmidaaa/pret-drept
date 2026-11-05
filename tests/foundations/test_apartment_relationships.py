import pytest
from fastapi.testclient import TestClient

import predict
from api import app
from rent_contracts import ContractError, validate_document


@pytest.fixture(
    params=[
        pytest.param(({"floor": 20, "total_floors": 3}, "floor"), id="floor-above-building"),
        pytest.param(({"area": 10, "kitchen_area": 60}, "kitchen_area"), id="kitchen-too-large"),
        pytest.param(({"lat": 47.02}, "lon"), id="latitude-only"),
        pytest.param(({"lat": None, "lon": 28.85}, "lat"), id="longitude-only"),
    ]
)
def invalid_relationship(request):
    return request.param


def _unexpected_bundle():
    pytest.fail("inconsistent apartment reached model loading")


def test_contract_rejects_inconsistent_apartment(apartment, invalid_relationship):
    changes, field = invalid_relationship
    with pytest.raises(ContractError, match=field):
        validate_document("apartment", apartment | changes)


def test_direct_prediction_rejects_before_model_load(apartment, invalid_relationship, monkeypatch):
    changes, field = invalid_relationship
    monkeypatch.setattr(predict, "get_bundle", _unexpected_bundle)
    with pytest.raises(ValueError, match=field):
        predict.run(apartment | changes)


def test_http_returns_field_error_without_echoing_input(
    apartment, invalid_relationship, monkeypatch
):
    changes, field = invalid_relationship
    categories = {"sector": [apartment["sector"]], "author": [apartment["author"]]}
    monkeypatch.setattr(predict, "known_values", categories.__getitem__)
    monkeypatch.setattr(predict, "get_bundle", _unexpected_bundle)

    with TestClient(app) as client:
        response = client.post("/predict", json=apartment | changes | {"note": "private example"})

    assert response.status_code == 422
    (error,) = response.json()["detail"]
    assert error["loc"] == ["body", field]
    assert error["msg"]
    assert "input" not in error
    assert "private example" not in response.text


@pytest.mark.parametrize(
    "optional_fields",
    [{}, {"lat": None, "lon": None}, {"lat": 47.02, "lon": 28.85}],
    ids=["omitted-coordinates", "null-coordinates", "complete-coordinates"],
)
def test_contract_accepts_equal_geometry_and_valid_coordinate_pairs(apartment, optional_fields):
    apartment.update(floor=9, total_floors=9, area=55, kitchen_area=55)
    validate_document("apartment", apartment | optional_fields)
