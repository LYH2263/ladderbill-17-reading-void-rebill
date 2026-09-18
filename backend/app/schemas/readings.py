from pydantic import BaseModel, Field


class VoidReadingRequest(BaseModel):
    reason: str = Field(min_length=1, description="作废原因必填")
