"""Macro-F1 scoring for spoof/live labels.

``True`` = spoof, ``False`` = live.  For each class
``F1 = 2TP / (2TP + FP + FN)`` (0 when the denominator is 0) and
``F1_macro = (F1_live + F1_spoof) / 2``.
"""

import uuid as uuid_lib
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, localcontext
from fractions import Fraction

from app.models import SCORE_SCALE

SCORE_QUANTUM = Decimal(1).scaleb(-SCORE_SCALE)  # 1e-20
DISPLAY_QUANTUM = Decimal("0.000001")


@dataclass(frozen=True)
class UuidSetDiff:
    missing: list[str]
    extra: list[str]

    @property
    def matches(self) -> bool:
        return not self.missing and not self.extra


def compare_uuid_sets(
    truth: Mapping[uuid_lib.UUID, bool], prediction: Mapping[uuid_lib.UUID, bool]
) -> UuidSetDiff:
    truth_keys = set(truth)
    pred_keys = set(prediction)
    missing = sorted(str(u) for u in truth_keys - pred_keys)
    extra = sorted(str(u) for u in pred_keys - truth_keys)
    return UuidSetDiff(missing=missing, extra=extra)


def _class_f1(tp: int, fp: int, fn: int) -> Fraction:
    denominator = 2 * tp + fp + fn
    if denominator == 0:
        return Fraction(0)
    return Fraction(2 * tp, denominator)


def f1_macro_fraction(
    truth: Mapping[uuid_lib.UUID, bool], prediction: Mapping[uuid_lib.UUID, bool]
) -> Fraction:
    """Exact macro-F1. Caller must ensure the UUID sets match."""
    tp_spoof = fp_spoof = fn_spoof = 0
    tp_live = fp_live = fn_live = 0
    for key, actual in truth.items():
        predicted = prediction[key]
        if actual and predicted:
            tp_spoof += 1
        elif actual and not predicted:
            fn_spoof += 1
            fp_live += 1
        elif not actual and predicted:
            fp_spoof += 1
            fn_live += 1
        else:
            tp_live += 1
    f1_spoof = _class_f1(tp_spoof, fp_spoof, fn_spoof)
    f1_live = _class_f1(tp_live, fp_live, fn_live)
    return (f1_live + f1_spoof) / 2


def fraction_to_score(value: Fraction) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = 50
        result = Decimal(value.numerator) / Decimal(value.denominator)
        return result.quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def f1_macro(
    truth: Mapping[uuid_lib.UUID, bool], prediction: Mapping[uuid_lib.UUID, bool]
) -> Decimal:
    return fraction_to_score(f1_macro_fraction(truth, prediction))


def format_score(score: Decimal) -> str:
    """Render a stored score with at most 6 decimal places."""
    return str(Decimal(score).quantize(DISPLAY_QUANTUM, rounding=ROUND_HALF_UP))
