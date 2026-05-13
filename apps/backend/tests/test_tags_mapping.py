from app.domain.tags import (
    ALL_TAGS_TO_DOMAIN,
    normalize_raw_message,
    TAG_SYNGAS_FLOW,
    TAG_EXHAUST_TEMP,
)


def test_control_tags_in_mapping():
    """제어 10개 태그 모두 도메인명으로 매핑된다."""
    assert ALL_TAGS_TO_DOMAIN[TAG_SYNGAS_FLOW] == "syngas_flow"


def test_output_tags_in_mapping():
    """출력 태그는 OutputVars 필드명으로 매핑된다 (ERD nox_ppm/power_mw가 아님)."""
    assert ALL_TAGS_TO_DOMAIN[TAG_EXHAUST_TEMP] == "exhaust_temp"


def test_normalize_raw_message_drops_unknown():
    """매핑 외 키는 dropped."""
    values = {
        TAG_SYNGAS_FLOW: 100.5,
        "IGCC.UNKNOWN.TAG": 999.0,
    }
    result = normalize_raw_message(values)
    assert result == {"syngas_flow": 100.5}


def test_normalize_raw_message_empty():
    assert normalize_raw_message({}) == {}
