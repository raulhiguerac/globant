from pydantic import BaseModel


class UploadResult(BaseModel):
    bucket: str
    key: str
