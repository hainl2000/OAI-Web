import uuid as uuid_lib

import pytest

from app.csv_utils import CsvValidationError, parse_labels_csv
from tests.helpers import make_csv, truth_rows

LIMITS = {"max_bytes": 5 * 1024 * 1024, "max_rows": 50_000}


def _parse(data: bytes, **overrides):
    return parse_labels_csv(data, **{**LIMITS, **overrides})


def _expect(code: str, data: bytes, **overrides):
    with pytest.raises(CsvValidationError) as exc:
        _parse(data, **overrides)
    assert exc.value.code == code, exc.value.message
    return exc.value


def test_parses_valid_file_and_preserves_order():
    rows = truth_rows(2, 2)
    parsed = _parse(make_csv(rows))
    assert list(parsed.labels.items()) == rows
    assert parsed.row_count == 4


def test_accepts_bom_crlf_and_reversed_columns():
    rows = truth_rows(1, 1)
    parsed = _parse(make_csv(rows, bom=True, newline="\r\n", header=("is_spoof", "uuid")))
    assert parsed.labels == dict(rows)


def test_labels_are_trimmed_and_case_insensitive():
    a, b = uuid_lib.uuid4(), uuid_lib.uuid4()
    data = f"uuid,is_spoof\n{a} ,  true \n {b},False\n".encode()
    parsed = _parse(data)
    assert parsed.labels == {a: True, b: False}


def test_blank_lines_are_ignored():
    rows = truth_rows(1, 1)
    data = make_csv(rows) + b"\n\n"
    assert _parse(data).row_count == 2


@pytest.mark.parametrize(
    "header",
    ["uuid", "uuid,is_spoof,extra", "id,is_spoof", "uuid,spoof", "uuid,is_spoof,is_spoof"],
)
def test_rejects_invalid_header(header):
    data = (header + "\n" + f"{uuid_lib.uuid4()},TRUE\n").encode()
    _expect("csv_invalid_header", data)


def test_rejects_invalid_uuid():
    data = b"uuid,is_spoof\nnot-a-uuid,TRUE\n"
    err = _expect("csv_invalid_uuid", data)
    assert err.details["line"] == 2


def test_rejects_duplicate_uuid_even_with_different_case():
    key = uuid_lib.uuid4()
    data = f"uuid,is_spoof\n{key},TRUE\n{str(key).upper()},FALSE\n".encode()
    err = _expect("csv_duplicate_uuid", data)
    assert err.details["line"] == 3


@pytest.mark.parametrize("label", ["yes", "1", "0", "", "T", "spoof"])
def test_rejects_invalid_boolean(label):
    data = f"uuid,is_spoof\n{uuid_lib.uuid4()},{label}\n".encode()
    _expect("csv_invalid_label", data)


def test_rejects_row_with_wrong_column_count():
    data = f"uuid,is_spoof\n{uuid_lib.uuid4()},TRUE,extra\n".encode()
    _expect("csv_row_malformed", data)


def test_rejects_empty_file_and_header_only():
    _expect("csv_empty", b"")
    _expect("csv_empty", b"   \n")
    _expect("csv_empty", b"uuid,is_spoof\n")


def test_rejects_non_utf8():
    data = b"uuid,is_spoof\n" + "é".encode("latin-1") + b",TRUE\n"
    _expect("csv_invalid_encoding", data)


def test_rejects_file_over_size_limit():
    data = make_csv(truth_rows(10, 10))
    _expect("csv_too_large", data, max_bytes=len(data) - 1)
    assert _parse(data, max_bytes=len(data)).row_count == 20


def test_rejects_too_many_rows():
    data = make_csv(truth_rows(3, 3))
    _expect("csv_too_many_rows", data, max_rows=5)
    assert _parse(data, max_rows=6).row_count == 6
