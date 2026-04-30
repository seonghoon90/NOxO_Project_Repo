from pydantic import BaseModel


class ThresholdResponse(BaseModel):
    nox_ppm_limit: float
