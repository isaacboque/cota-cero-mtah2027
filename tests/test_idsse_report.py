import numpy as np

from external.idsse_report import label_counts


def test_label_counts_split_by_code_and_coverage():
    d = {"gt_codes": np.array([0, 0, 1, 2, 2, 2, -1], dtype=np.int8),
         "ball_seen": np.array([1, 1, 0, 1, 0, 0, 1], dtype=bool)}
    c = label_counts(d)
    assert (c["H"], c["A"], c["D"], c["unknown"], c["n"]) == (2, 1, 3, 1, 7)
    assert abs(c["labelled_share"] - 6 / 7) < 1e-9
    assert abs(c["ball_seen_share"] - 4 / 7) < 1e-9
