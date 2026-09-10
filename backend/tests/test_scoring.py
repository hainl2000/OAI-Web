import random
import uuid as uuid_lib
from decimal import Decimal
from fractions import Fraction

from app.scoring import compare_uuid_sets, f1_macro, f1_macro_fraction, format_score


def _labels(pairs):
    return {uuid_lib.UUID(int=i): v for i, v in pairs}


def test_perfect_prediction_scores_one():
    truth = _labels([(1, True), (2, False), (3, True), (4, False)])
    assert f1_macro_fraction(truth, dict(truth)) == Fraction(1)
    assert f1_macro(truth, dict(truth)) == Decimal("1.00000000000000000000")


def test_completely_wrong_prediction_scores_zero():
    truth = _labels([(1, True), (2, False), (3, True), (4, False)])
    prediction = {k: (not v) for k, v in truth.items()}
    assert f1_macro_fraction(truth, prediction) == Fraction(0)
    assert f1_macro(truth, prediction) == Decimal(0)


def test_class_imbalance_uses_macro_average():
    # 9 spoof, 1 live. Predict everything spoof.
    truth = _labels([(i, True) for i in range(1, 10)] + [(10, False)])
    prediction = {k: True for k in truth}
    # spoof: TP=9, FP=1, FN=0 -> F1 = 18/19 ; live: TP=0 -> F1 = 0
    expected = (Fraction(18, 19) + Fraction(0)) / 2
    assert f1_macro_fraction(truth, prediction) == expected
    assert f1_macro(truth, prediction) == Decimal("0.47368421052631578947")


def test_zero_denominator_class_gets_zero_f1():
    # Only live samples in the truth and prediction: spoof class has TP=FP=FN=0.
    truth = _labels([(1, False), (2, False), (3, False)])
    prediction = dict(truth)
    # live F1 = 1, spoof F1 = 0 -> macro = 0.5
    assert f1_macro_fraction(truth, prediction) == Fraction(1, 2)
    assert f1_macro(truth, prediction) == Decimal("0.5")


def test_partial_mistakes_are_exact():
    truth = _labels([(1, True), (2, True), (3, False), (4, False)])
    prediction = dict(truth)
    prediction[uuid_lib.UUID(int=1)] = False  # one spoof predicted as live
    # spoof: TP=1 FP=0 FN=1 -> 2/3 ; live: TP=2 FP=1 FN=0 -> 4/5
    expected = (Fraction(2, 3) + Fraction(4, 5)) / 2
    assert f1_macro_fraction(truth, prediction) == expected
    assert f1_macro(truth, prediction) == Decimal("0.73333333333333333333")


def test_uuid_order_does_not_matter():
    truth = _labels([(i, i % 3 == 0) for i in range(1, 51)])
    prediction_items = list(truth.items())
    random.Random(42).shuffle(prediction_items)
    prediction = dict(prediction_items)
    prediction[uuid_lib.UUID(int=7)] = not prediction[uuid_lib.UUID(int=7)]
    assert f1_macro(truth, prediction) == f1_macro(truth, dict(sorted(prediction.items())))
    assert f1_macro(truth, prediction) < Decimal(1)


def test_compare_uuid_sets_reports_missing_and_extra():
    truth = _labels([(1, True), (2, False)])
    prediction = _labels([(2, False), (3, True)])
    diff = compare_uuid_sets(truth, prediction)
    assert diff.missing == [str(uuid_lib.UUID(int=1))]
    assert diff.extra == [str(uuid_lib.UUID(int=3))]
    assert not diff.matches
    assert compare_uuid_sets(truth, dict(truth)).matches


def test_format_score_rounds_to_six_decimals():
    assert format_score(Decimal("0.47368421052631578947")) == "0.473684"
    assert format_score(Decimal("1")) == "1.000000"
    assert format_score(Decimal("0.6666665")) == "0.666667"
