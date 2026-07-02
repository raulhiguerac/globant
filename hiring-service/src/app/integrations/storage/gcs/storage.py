import os
from typing import Any, BinaryIO, Dict, Generator, Optional

from google.cloud import storage as gcs

from app.core.exceptions.storage import StorageMisconfiguredError
from app.services.shared.schemas.storage import UploadResult


class StorageClient:
    def __init__(self) -> None:
        project = os.getenv("GCS_PROJECT")
        if not project:
            raise StorageMisconfiguredError(context={"missing": "GCS_PROJECT"})

        self.client = gcs.Client(project=project)

    def upload_file(
        self,
        *,
        fileobj: BinaryIO,
        bucket: str,
        key: str,
        extra_args: Optional[Dict[str, Any]] = None,
    ) -> UploadResult:
        if hasattr(fileobj, "seek"):
            try:
                fileobj.seek(0)
            except Exception:
                pass

        blob = self.client.bucket(bucket).blob(key)
        blob.upload_from_file(fileobj)
        return UploadResult(bucket=bucket, key=key)

    def stream_file(self, *, bucket: str, key: str) -> Generator[bytes, None, None]:
        blob = self.client.bucket(bucket).blob(key)
        with blob.open("rb") as f:
            while chunk := f.read(8192):
                yield chunk
