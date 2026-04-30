from pydantic import BaseModel


class AckResponse(BaseModel):
    ack: bool = True


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
