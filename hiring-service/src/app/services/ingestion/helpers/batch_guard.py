from fastapi import HTTPException, status

_MAX_ROWS = 1000


def validate_batch(records: list) -> None:
    if not records:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No valid rows found")
    if len(records) > _MAX_ROWS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Max {_MAX_ROWS} rows per request")
