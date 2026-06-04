from __future__ import annotations

from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    first_job_id: str = Field(..., examples=["uuid"])
    second_job_id: str | None = Field(None, examples=["uuid"])
    first_frame: int | None = None
    second_frame: int | None = None
