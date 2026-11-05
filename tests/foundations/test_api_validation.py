import pytest
from fastapi.testclient import TestClient

import predict
from api import app


@pytest.fixture
def validation_client(monkeypatch):
    categories = {"sector": ["centru"], "author": ["owner"]}
    monkeypatch.setattr(predict, "known_values", categories.__getitem__)

    def unexpected_prediction(_):
        pytest.fail("invalid input reached prediction")

    monkeypatch.setattr(predict, "run", unexpected_prediction)
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def _post_area(client, raw_area):
    body = (
        '{"rooms":2,"area":' + raw_area + ',"floor":3,"total_floors":9,'
        '"sector":"centru","author":"owner"}'
    )
    return client.post("/predict", content=body, headers={"content-type": "application/json"})


@pytest.mark.parametrize(
    ("raw_area", "expected_input"),
    [
        ("NaN", None),
        ("Infinity", None),
        ("-Infinity", None),
        ("1e999", None),
        ('[NaN, {"other": -Infinity}, 2.5, "NaN"]', [None, {"other": None}, 2.5, "NaN"]),
    ],
)
def test_nonfinite_inputs_return_json_validation_errors(
    validation_client, raw_area, expected_input
):
    response = _post_area(validation_client, raw_area)

    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"
    (error,) = response.json()["detail"]
    assert error["loc"] == ["body", "area"]
    assert error["input"] == expected_input
    assert error["type"]
    assert error["msg"]


def test_finite_validation_error_preserves_detail(validation_client):
    response = _post_area(validation_client, "-5.25")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "greater_than_equal",
                "loc": ["body", "area"],
                "msg": "Input should be greater than or equal to 10",
                "input": -5.25,
                "ctx": {"ge": 10.0},
            }
        ]
    }
