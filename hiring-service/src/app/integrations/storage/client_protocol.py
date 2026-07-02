from typing import Any, BinaryIO, Dict, Generator, Optional, Protocol

from app.services.shared.schemas.storage import UploadResult


class StorageClientProtocol(Protocol):
    def upload_file(
        self,
        *,
        fileobj: BinaryIO,
        bucket: str,
        key: str,
        extra_args: Optional[Dict[str, Any]] = None,
    ) -> UploadResult: ...

    def stream_file(self, *, bucket: str, key: str) -> Generator[bytes, None, None]: ...
