from unittest.mock import MagicMock, patch

from app.integrations.duckdb.client import DuckDbClient

MODULE = "app.integrations.duckdb.client"


def _query_result(rows):
    result = MagicMock()
    result.description = [("id",)]
    result.fetchall = MagicMock(return_value=rows)
    return result


def _connectable_conn(query_effect):
    # INSTALL/LOAD/ATTACH succeed; the 4th execute() resolves to query_effect.
    conn = MagicMock()
    conn.execute = MagicMock(side_effect=[MagicMock(), MagicMock(), MagicMock(), query_effect])
    return conn


def test_connect_installs_loads_and_attaches_postgres():
    conn = _connectable_conn(_query_result([]))
    with patch(f"{MODULE}.duckdb.connect", MagicMock(return_value=conn)):
        DuckDbClient()

    calls = [c.args[0] for c in conn.execute.call_args_list]
    assert calls[0] == "INSTALL postgres;"
    assert calls[1] == "LOAD postgres;"
    assert calls[2].startswith("ATTACH")


def test_query_returns_rows_on_healthy_connection():
    conn = _connectable_conn(_query_result([(1,), (2,)]))
    with patch(f"{MODULE}.duckdb.connect", MagicMock(return_value=conn)):
        client = DuckDbClient()
        rows = client.query(sql="SELECT id FROM pg.employees")

    assert rows == [{"id": 1}, {"id": 2}]


def test_query_reconnects_and_retries_on_broken_connection():
    broken_conn = _connectable_conn(RuntimeError("connection lost"))
    healthy_conn = _connectable_conn(_query_result([(1,)]))

    with patch(f"{MODULE}.duckdb.connect", MagicMock(side_effect=[broken_conn, healthy_conn])):
        client = DuckDbClient()
        rows = client.query(sql="SELECT id FROM pg.employees")

    assert rows == [{"id": 1}]


def test_query_raises_if_reconnect_also_fails():
    broken_conn = _connectable_conn(RuntimeError("connection lost"))
    still_broken_conn = _connectable_conn(RuntimeError("still down"))

    with patch(f"{MODULE}.duckdb.connect", MagicMock(side_effect=[broken_conn, still_broken_conn])):
        client = DuckDbClient()
        try:
            client.query(sql="SELECT id FROM pg.employees")
            assert False, "expected RuntimeError to propagate"
        except RuntimeError as exc:
            assert str(exc) == "still down"
