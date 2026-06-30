"""科类口径兼容工具。

早期数据可能使用“理科 / 文科”，新高考数据更常见“物理类 / 历史类”。
正式 admissions 数据尽量保存为新口径；推荐查询同时兼容新旧口径。
"""


def normalize_subject_type(subject_type: str | None) -> str | None:
    """把常见旧口径科类规范化为新高考口径。"""
    if subject_type is None:
        return None

    cleaned = str(subject_type).strip()
    if cleaned in {"理科", "物理", "物理类"}:
        return "物理类"
    if cleaned in {"文科", "历史", "历史类"}:
        return "历史类"
    return cleaned


def get_subject_type_aliases(subject_type: str | None) -> list[str]:
    """返回推荐查询时需要同时匹配的科类别名。"""
    normalized = normalize_subject_type(subject_type)
    if not normalized:
        return []

    if normalized == "物理类":
        values = ["物理类", "理科"]
    elif normalized == "历史类":
        values = ["历史类", "文科"]
    else:
        values = [normalized]

    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result
