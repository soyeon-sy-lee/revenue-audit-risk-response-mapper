from __future__ import annotations


def grade_to_label(grade: int) -> str:
    if grade >= 3:
        return "core"
    if grade == 2:
        return "supporting"
    if grade == 1:
        return "conditional"
    if grade == 0:
        return "weak_match"
    return "not_applicable"
