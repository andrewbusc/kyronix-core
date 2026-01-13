from datetime import date

from pydantic import BaseModel, ConfigDict


class PaystubSummary(BaseModel):
    id: int
    pay_date: date
    pay_period_start: date
    pay_period_end: date
    file_name: str

    model_config = ConfigDict(from_attributes=True)


class PaystubListResponse(BaseModel):
    items: list[PaystubSummary]
    available_years: list[int]
