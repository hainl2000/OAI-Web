from app.csv_utils import CsvValidationError
from app.errors import ApiError


def csv_error_to_api(exc: CsvValidationError) -> ApiError:
    return ApiError(422, exc.code, exc.message, **exc.details)
