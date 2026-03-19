from pydantic import BaseModel


class ProxyErrorResponse(BaseModel):
    error: str
    message: str
    route: str
