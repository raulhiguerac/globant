from datetime import datetime, timezone

from app.services.ingestion.helpers.csv_parser import parse_departments, parse_employees, parse_jobs


# ---------------------------------------------------------------------------
# parse_departments
# ---------------------------------------------------------------------------

def test_parse_departments_valid():
    raw = b"1,Engineering\n2,HR"
    records, errors = parse_departments(raw)
    assert len(records) == 2
    assert errors == []
    assert records[0].id == 1
    assert records[0].department == "Engineering"


def test_parse_departments_invalid_row_goes_to_errors():
    raw = b"1,Engineering\nnot_an_id,HR"
    records, errors = parse_departments(raw)
    assert len(records) == 1
    assert len(errors) == 1
    assert "row 2" in errors[0]


def test_parse_departments_empty():
    records, errors = parse_departments(b"")
    assert records == []
    assert errors == []


# ---------------------------------------------------------------------------
# parse_jobs
# ---------------------------------------------------------------------------

def test_parse_jobs_valid():
    raw = b"1,Recruiter\n2,Manager"
    records, errors = parse_jobs(raw)
    assert len(records) == 2
    assert errors == []
    assert records[1].job == "Manager"


def test_parse_jobs_missing_column_goes_to_errors():
    raw = b"1\n2,Manager"
    records, errors = parse_jobs(raw)
    assert len(records) == 1
    assert len(errors) == 1


# ---------------------------------------------------------------------------
# parse_employees
# ---------------------------------------------------------------------------

def test_parse_employees_valid_iso_z():
    raw = b"1,Harold Vogt,2021-11-07T02:48:42Z,2,96"
    records, errors = parse_employees(raw)
    assert len(records) == 1
    assert errors == []
    assert records[0].id == 1
    assert records[0].hiring_datetime == datetime(2021, 11, 7, 2, 48, 42, tzinfo=timezone.utc)
    assert records[0].department_id == 2
    assert records[0].job_id == 96


def test_parse_employees_empty_job_id_goes_to_errors():
    raw = b"2,Ty Hofer,2021-05-30T05:43:46Z,8,"
    records, errors = parse_employees(raw)
    assert records == []
    assert len(errors) == 1
    assert "row 1" in errors[0]


def test_parse_employees_empty_department_id_goes_to_errors():
    raw = b"3,Lyman,2021-09-01T23:27:38Z,,52"
    records, errors = parse_employees(raw)
    assert records == []
    assert len(errors) == 1


def test_parse_employees_mixed_valid_and_invalid():
    raw = b"1,Harold,2021-11-07T02:48:42Z,2,96\n2,Ty,2021-05-30T05:43:46Z,8,"
    records, errors = parse_employees(raw)
    assert len(records) == 1
    assert len(errors) == 1


def test_parse_employees_empty():
    records, errors = parse_employees(b"")
    assert records == []
    assert errors == []
