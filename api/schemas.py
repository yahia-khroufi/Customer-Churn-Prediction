
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.common.data_contract import CATEGORY_VALUES


NonNegativeAmount = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class CustomerInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    gender: str
    SeniorCitizen: Annotated[int, Field(strict=True, ge=0, le=1)]
    Partner: str
    Dependents: str
    tenure: Annotated[int, Field(strict=True, ge=0)]
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: NonNegativeAmount
    TotalCharges: NonNegativeAmount | None = None

    @model_validator(mode="after")
    def validate_categories_and_services(self):
        for column, allowed in CATEGORY_VALUES.items():
            if getattr(self, column) not in allowed:
                raise ValueError(f"{column} : valeurs autorisées {allowed}.")
        if (self.PhoneService == "No") != (self.MultipleLines == "No phone service"):
            raise ValueError("PhoneService et MultipleLines sont incohérents.")
        for column in ["OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies"]:
            if (self.InternetService == "No") != (getattr(self, column) == "No internet service"):
                raise ValueError(f"InternetService et {column} sont incohérents.")
        return self


class PredictionOutput(BaseModel):
    prediction: Literal["Yes", "No"]
    churn_probability: Annotated[float, Field(ge=0, le=1)]
    threshold: float
    model_name: str
