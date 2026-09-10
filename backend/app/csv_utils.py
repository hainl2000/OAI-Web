"""Parsing and validation of ``uuid,is_spoof`` label CSV files.

The same rules apply to the admin answer key and to candidate prediction files.
"""

import csv
import io
import uuid as uuid_lib
from dataclasses import dataclass, field
from typing import Any

REQUIRED_COLUMNS = ("uuid", "is_spoof")
TRUE_VALUES = {"true"}
FALSE_VALUES = {"false"}


class CsvValidationError(Exception):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass
class ParsedCsv:
    """Validated label rows. ``labels`` preserves file order; ``True`` means spoof."""

    labels: dict[uuid_lib.UUID, bool] = field(default_factory=dict)

    @property
    def row_count(self) -> int:
        return len(self.labels)


def _decode(data: bytes) -> str:
    try:
        # utf-8-sig transparently strips a UTF-8 BOM when present.
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvValidationError(
            "csv_invalid_encoding", "File phải được mã hoá UTF-8 (có hoặc không có BOM)."
        ) from exc


def parse_labels_csv(data: bytes, *, max_bytes: int, max_rows: int) -> ParsedCsv:
    if len(data) > max_bytes:
        raise CsvValidationError(
            "csv_too_large",
            f"File vượt quá kích thước tối đa {max_bytes // (1024 * 1024)} MB.",
            max_bytes=max_bytes,
            size_bytes=len(data),
        )
    if not data.strip():
        raise CsvValidationError("csv_empty", "File CSV rỗng.")

    text = _decode(data)
    reader = csv.reader(io.StringIO(text, newline=""))

    try:
        header = next(reader)
    except StopIteration:
        raise CsvValidationError("csv_empty", "File CSV rỗng.")
    except csv.Error as exc:
        raise CsvValidationError("csv_malformed", f"Không đọc được CSV: {exc}") from exc

    header = [h.strip() for h in header]
    if sorted(header) != sorted(REQUIRED_COLUMNS):
        raise CsvValidationError(
            "csv_invalid_header",
            "Header phải gồm đúng hai cột `uuid` và `is_spoof`.",
            header=header,
        )
    uuid_idx = header.index("uuid")
    spoof_idx = header.index("is_spoof")

    labels: dict[uuid_lib.UUID, bool] = {}
    line_no = 1  # header is line 1
    try:
        for row in reader:
            line_no += 1
            if not row or all(not cell.strip() for cell in row):
                continue  # ignore blank lines
            if len(row) != 2:
                raise CsvValidationError(
                    "csv_row_malformed",
                    f"Dòng {line_no} phải có đúng 2 cột.",
                    line=line_no,
                )
            if len(labels) >= max_rows:
                raise CsvValidationError(
                    "csv_too_many_rows",
                    f"File vượt quá {max_rows} dòng dữ liệu.",
                    max_rows=max_rows,
                )

            raw_uuid = row[uuid_idx].strip()
            try:
                parsed_uuid = uuid_lib.UUID(raw_uuid)
            except (ValueError, AttributeError, TypeError):
                raise CsvValidationError(
                    "csv_invalid_uuid",
                    f"Dòng {line_no}: uuid không hợp lệ.",
                    line=line_no,
                    value=raw_uuid,
                )
            if parsed_uuid in labels:
                raise CsvValidationError(
                    "csv_duplicate_uuid",
                    f"Dòng {line_no}: uuid bị trùng.",
                    line=line_no,
                    value=str(parsed_uuid),
                )

            raw_label = row[spoof_idx].strip().lower()
            if raw_label in TRUE_VALUES:
                is_spoof = True
            elif raw_label in FALSE_VALUES:
                is_spoof = False
            else:
                raise CsvValidationError(
                    "csv_invalid_label",
                    f"Dòng {line_no}: is_spoof chỉ nhận TRUE hoặc FALSE.",
                    line=line_no,
                    value=row[spoof_idx],
                )
            labels[parsed_uuid] = is_spoof
    except csv.Error as exc:
        raise CsvValidationError("csv_malformed", f"Không đọc được CSV: {exc}") from exc

    if not labels:
        raise CsvValidationError("csv_empty", "File CSV không có dòng dữ liệu nào.")
    return ParsedCsv(labels=labels)
