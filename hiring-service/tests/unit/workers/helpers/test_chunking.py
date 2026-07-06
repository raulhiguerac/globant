from app.workers.helpers.chunking import iter_chunks


def test_splits_into_even_chunks():
    assert list(iter_chunks([1, 2, 3, 4], 2)) == [[1, 2], [3, 4]]


def test_last_chunk_is_partial():
    assert list(iter_chunks([1, 2, 3], 2)) == [[1, 2], [3]]


def test_empty_list_yields_nothing():
    assert list(iter_chunks([], 10)) == []


def test_size_larger_than_list_yields_single_chunk():
    assert list(iter_chunks([1, 2], 10)) == [[1, 2]]
