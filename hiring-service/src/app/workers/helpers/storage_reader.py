from app.services.shared.ports.storage import StoragePort


async def download_file(*, storage: StoragePort, bucket: str, key: str) -> bytes:
    chunks: list[bytes] = []
    async for chunk in await storage.stream_file(bucket=bucket, key=key):
        chunks.append(chunk)
    return b"".join(chunks)
