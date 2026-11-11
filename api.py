"""Browser form and HTTP endpoints using the shared rent predictor."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator

import predict

app = FastAPI(title="Fair Chisinau Rent", description="Overpriced apartment?")

HOMEPAGE = Path(__file__).resolve().parent / "app"


@app.exception_handler(predict.ModelUnavailableError)
async def model_unavailable(
    _request: Request, _error: predict.ModelUnavailableError
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Prediction model unavailable. Check the server model configuration."
        },
    )


@app.get("/options")
def options():
    # the dropdown values, read straight from the trained model so they always match
    return {
        column: predict.known_values(column)
        for column in ("sector", "building_fund", "condition", "author")
    }


@app.get("/")
def home():
    # the one-page website (form -> fair rent + verdict)
    return FileResponse(HOMEPAGE / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


class Apartment(BaseModel):
    rooms: float = Field(ge=1, le=6)
    area: float = Field(ge=10, le=400)
    floor: float = Field(ge=1, le=50)
    total_floors: float = Field(ge=1, le=50)
    sector: str
    author: str  # agency / owner / developer - always known to the user
    building_fund: str = "secundar"
    condition: str = "necunoscut"
    autonomous_heating: int = Field(0, ge=0, le=1)
    furnished: int = Field(0, ge=0, le=1)
    elevator: int = Field(0, ge=0, le=1)
    parking: int = Field(0, ge=0, le=1)
    price: float | None = Field(None, gt=0, le=50000)  # asking monthly rent in EUR
    air_conditioning: int = Field(0, ge=0, le=1)
    floor_heating: int = Field(0, ge=0, le=1)
    terrace: int = Field(0, ge=0, le=1)
    panoramic_windows: int = Field(0, ge=0, le=1)
    utilities_included: int = Field(0, ge=0, le=1)  # rent includes utilities
    lux: int = Field(0, ge=0, le=1)  # premium building or finishes
    balcony_count: int = Field(0, ge=0, le=4)
    bathrooms: int = Field(1, ge=1, le=4)
    kitchen_area: float | None = Field(None, ge=3, le=60)
    ceiling_height: float | None = Field(None, ge=2, le=4.5)

    # exact gps coordinates (must be inside chisinau)
    lat: float | None = Field(None, ge=46.9, le=47.1)
    lon: float | None = Field(None, ge=28.74, le=28.95)

    @field_validator("sector", "author", "building_fund", "condition")
    @classmethod
    def category_the_model_knows(cls, value, info):
        # Reject unseen categories: one-hot encoding would silently turn them into zeros.
        value = value.strip().lower()
        allowed = predict.known_values(info.field_name)
        if value not in allowed:
            raise ValueError(
                f"unknown {info.field_name} '{value}', expected one of: {', '.join(allowed)}"
            )
        return value


@app.post("/predict")
def make_prediction(apartment: Apartment):
    # predict.run derives is_ground/is_top from the floors itself
    return predict.run(apartment.model_dump())
