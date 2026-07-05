from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from typing import Optional
import os

import predict

app = FastAPI(title='Fair Chisinau Rent', description='Overpriced apartment?')

HOMEPAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")

@app.get("/options")
def options():
    # the dropdown values, read straight from the trained model so they always match
    return {c: predict.known_values(c) for c in ["sector", "building_fund", "condition"]}

@app.get("/")
def home():
    # the one-page website (form -> fair rent + verdict)
    return FileResponse(os.path.join(HOMEPAGE, "index.html"))

@app.get("/health")
def health():
    return {"status": "ok"}

class Apartment(BaseModel):
    rooms: float = Field(ge=1, le=6)
    area: float = Field(ge=10, le=400)
    floor: float = Field(ge=1, le=50)
    total_floors: float = Field(ge=1, le=50)
    sector: str
    building_fund: str = "secundar"
    condition: str = "necunoscut"
    autonomous_heating: int = Field(0, ge=0, le=1)
    furnished: int = Field(0, ge=0, le=1)
    elevator: int = Field(0, ge=0, le=1)
    parking: int = Field(0, ge=0, le=1)
    price: Optional[float] = Field(None, gt=0, le=50000) # asking monthly rent in EUR


    air_conditioning: int = Field(0, ge=0, le=1)
    floor_heating: int = Field(0, ge=0, le=1)
    terrace: int = Field(0, ge=0, le=1)
    panoramic_windows: int = Field(0, ge=0, le=1)
    utilities_included: int = Field(0, ge=0, le=1) # rent includes utilities
    balcony_count: int = Field(0, ge=0, le=4)
    kitchen_area: Optional[float] = Field(None, ge=3, le=60)
    ceiling_height: Optional[float] = Field(None, ge=2, le=4.5)

    # exact gps coordinates (must be inside chisinau) 
    lat: Optional[float] = Field(None, ge=46.9, le=47.1)
    lon: Optional[float] = Field(None, ge=28.74, le=28.95)

    @field_validator("sector", "building_fund", "condition")
    @classmethod
    def category_the_model_knows(cls, value, info):
        # a category the model never saw would silently one-hot to all zeros and
        # produce a confident-looking nonsense prediction. better to refuse loudly.
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