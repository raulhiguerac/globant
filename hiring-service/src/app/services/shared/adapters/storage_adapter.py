import asyncio
from typing import IO, Any, AsyncIterator, Dict, Optional

from fastapi.concurrency import run_in_threadpool

from app.integrations.storage.client_protocol import StorageClientProtocol
from app.services.shared.ports.storage import StoragePort
from app.services.shared.schemas.storage import UploadResult


class StorageAdapter(StoragePort):
    def __init__(self, *, client: StorageClientProtocol) -> None:
        self._client = client

    async def upload_file(
        self,
        *,
        fileobj: IO[bytes],
        bucket: str,
        key: str,
        extra_args: Optional[Dict[str, Any]] = None,
    ) -> UploadResult:
        return await run_in_threadpool(
            self._client.upload_file,
            fileobj=fileobj,
            bucket=bucket,
            key=key,
            extra_args=extra_args,
        )

    async def stream_file(self, *, bucket: str, key: str) -> AsyncIterator[bytes]:
        loop = asyncio.get_event_loop()
        sync_gen = await run_in_threadpool(self._client.stream_file, bucket=bucket, key=key)

        async def _async_gen() -> AsyncIterator[bytes]:
            for chunk in sync_gen:
                yield chunk
                await asyncio.sleep(0)

        return _async_gen()
