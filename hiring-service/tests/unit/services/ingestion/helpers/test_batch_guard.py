import pytest
from fastapi import HTTPException

from app.services.ingestion.helpers.batch_guard import validate_batch


def test_valid_batch_passes():
    validate_batch([object()] * 10)


def test_empty_batch_raises_422():
    with pytest.raises(HTTPException) as exc_info:
        validate_batch([])
    assert exc_info.value.status_code == 422


def test_over_limit_raises_422():
    with pytest.raises(HTTPException) as exc_info:
        validate_batch([object()] * 1001)
    assert exc_info.value.status_code == 422


def test_exactly_1000_passes():
    validate_batch([object()] * 1000)
