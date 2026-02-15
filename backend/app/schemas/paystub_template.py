from pydantic import BaseModel, ConfigDict


class PaystubTemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    sections: list[str]

    model_config = ConfigDict(extra="forbid")


class PaystubTemplateListResponse(BaseModel):
    items: list[PaystubTemplateInfo]

    model_config = ConfigDict(extra="forbid")
