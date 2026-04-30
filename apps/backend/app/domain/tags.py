"""IGCC 태그 매핑 / 운영 한계 / 입력 검증.

도메인 객체(ControlVars, OutputVars, SimulationState)는 `digital_twin.simulation`이
SoT(Single Source of Truth). 본 모듈은 백엔드 전용 책임만 담당한다:

1. IGCC.CC.G1.* 태그 상수 정의 (프론트 ↔ 백엔드 식별자)
2. ControlVars ↔ 태그 dict 양방향 매핑
3. ControlBounds (운영 한계) + validate_control (입력 검증)
"""

from dataclasses import dataclass
from typing import Final

from digital_twin.simulation import ControlVars


# ============================================================
# 제어 변수 태그 (프론트 → 백엔드)
# ============================================================
TAG_SYNGAS_FLOW: Final[str] = "IGCC.CC.G1.ca_fqsg_cl"          # 합성가스 유량
TAG_N2_OFFSET: Final[str] = "IGCC.CC.G1.NQKR3_MONITOR"        # 질소가스 주입 오프셋
TAG_IGV_OPENING: Final[str] = "IGCC.CC.G1.csgv"               # IGV 개도

CONTROL_TAGS: Final[tuple[str, ...]] = (
    TAG_SYNGAS_FLOW,
    TAG_N2_OFFSET,
    TAG_IGV_OPENING,
)


# ============================================================
# 출력 변수 태그
# ============================================================
TAG_POWER: Final[str] = "IGCC.CC.G1.DWATT"  # 발전량 (MW)


# ============================================================
# ControlVars ↔ 태그 dict 매핑
# DT의 ControlVars는 IGCC 태그 체계를 모르므로 매핑은 본 모듈이 책임진다.
# ============================================================
def control_vars_from_tag_dict(tags: dict[str, float]) -> ControlVars:
    """IGCC 태그 dict → DT ControlVars."""
    return ControlVars(
        syngas_flow=tags[TAG_SYNGAS_FLOW],
        n2_offset=tags[TAG_N2_OFFSET],
        igv_opening=tags[TAG_IGV_OPENING],
    )


def control_vars_to_tag_dict(vars: ControlVars) -> dict[str, float]:
    """DT ControlVars → IGCC 태그 dict."""
    return {
        TAG_SYNGAS_FLOW: vars.syngas_flow,
        TAG_N2_OFFSET: vars.n2_offset,
        TAG_IGV_OPENING: vars.igv_opening,
    }


# ============================================================
# 변수별 운영 한계 (기본값) — [추후 결정]
# 프론트의 ▲▼ 버튼 한계 도달 비활성화 로직과 일치시킨다.
# ============================================================
@dataclass(frozen=True)
class ControlBounds:
    syngas_flow_min: float = 800.0
    syngas_flow_max: float = 2200.0
    n2_offset_min: float = 0.0
    n2_offset_max: float = 500.0
    igv_opening_min: float = 30.0
    igv_opening_max: float = 100.0


DEFAULT_CONTROL_BOUNDS: Final[ControlBounds] = ControlBounds()


def validate_control(
    vars: ControlVars, bounds: ControlBounds = DEFAULT_CONTROL_BOUNDS
) -> list[str]:
    """범위를 벗어난 값에 대한 에러 메시지 목록을 반환. 빈 리스트면 정상."""
    errors: list[str] = []
    if not (bounds.syngas_flow_min <= vars.syngas_flow <= bounds.syngas_flow_max):
        errors.append(
            f"{TAG_SYNGAS_FLOW}={vars.syngas_flow} out of range "
            f"[{bounds.syngas_flow_min}, {bounds.syngas_flow_max}]"
        )
    if not (bounds.n2_offset_min <= vars.n2_offset <= bounds.n2_offset_max):
        errors.append(
            f"{TAG_N2_OFFSET}={vars.n2_offset} out of range "
            f"[{bounds.n2_offset_min}, {bounds.n2_offset_max}]"
        )
    if not (bounds.igv_opening_min <= vars.igv_opening <= bounds.igv_opening_max):
        errors.append(
            f"{TAG_IGV_OPENING}={vars.igv_opening} out of range "
            f"[{bounds.igv_opening_min}, {bounds.igv_opening_max}]"
        )
    return errors
