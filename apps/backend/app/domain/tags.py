"""IGCC 태그 매핑 / 운영 한계 / 입력 검증.

도메인 객체(ControlVars, OutputVars, SimulationState)는 `digital_twin.simulation`이
SoT(Single Source of Truth). 본 모듈은 백엔드 전용 책임만 담당한다:

1. IGCC.CC.G1.* 태그 상수 정의 (프론트 ↔ 백엔드 식별자)
2. ControlVars ↔ 태그 dict 양방향 매핑 (10개 변수)
3. ControlBounds (운영 한계) + validate_control (입력 검증)

신규 7개 제어 변수의 단위/한계는 [추후 결정] — 가안 임의값 채택.
"""

from dataclasses import dataclass
from typing import Final

from digital_twin.simulation import ControlVars


# ============================================================
# 제어 변수 태그 (프론트 → 백엔드) — 10개
# 출처: DT_ARCHITECTURE.md §4 ControlVars
# ============================================================
TAG_SYNGAS_FLOW: Final[str] = "IGCC.CC.G1.ca_fqsg_cl"          # 합성가스 유량
TAG_IGV_OPENING: Final[str] = "IGCC.CC.G1.csgv"               # IGV 개도
TAG_N2_OFFSET: Final[str] = "IGCC.CC.G1.NQKR3_MONITOR"        # N2 오프셋
TAG_N2_VALVE_1: Final[str] = "IGCC.CC.G1.nicvs1"              # N2 주입 제어밸브 #1
TAG_SYNGAS_SRV: Final[str] = "IGCC.CC.G1.FSAGR"               # Syngas SRV(VSR-11)
TAG_SYNGAS_GCV_1: Final[str] = "IGCC.CC.G1.FSAG11"            # Syngas GCV #1
TAG_SYNGAS_GCV_1A: Final[str] = "IGCC.CC.G1.FSAG11A"          # Syngas GCV #1A
TAG_SYNGAS_GCV_2: Final[str] = "IGCC.CC.G1.FSAG12"            # Syngas GCV #2
TAG_IBH_VALVE: Final[str] = "IGCC.CC.G1.CSBHX"                # IBH 입구 가열 제어밸브
TAG_N2_FLOW: Final[str] = "IGCC.CC.G1.NQJ"                    # N2 주입 유량

CONTROL_TAGS: Final[tuple[str, ...]] = (
    TAG_SYNGAS_FLOW,
    TAG_IGV_OPENING,
    TAG_N2_OFFSET,
    TAG_N2_VALVE_1,
    TAG_SYNGAS_SRV,
    TAG_SYNGAS_GCV_1,
    TAG_SYNGAS_GCV_1A,
    TAG_SYNGAS_GCV_2,
    TAG_IBH_VALVE,
    TAG_N2_FLOW,
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
    """IGCC 태그 dict → DT ControlVars (10개 필드)."""
    return ControlVars(
        syngas_flow=tags[TAG_SYNGAS_FLOW],
        igv_opening=tags[TAG_IGV_OPENING],
        n2_offset=tags[TAG_N2_OFFSET],
        n2_valve_1=tags[TAG_N2_VALVE_1],
        syngas_srv=tags[TAG_SYNGAS_SRV],
        syngas_gcv_1=tags[TAG_SYNGAS_GCV_1],
        syngas_gcv_1a=tags[TAG_SYNGAS_GCV_1A],
        syngas_gcv_2=tags[TAG_SYNGAS_GCV_2],
        ibh_valve=tags[TAG_IBH_VALVE],
        n2_flow=tags[TAG_N2_FLOW],
    )


def control_vars_to_tag_dict(vars: ControlVars) -> dict[str, float]:
    """DT ControlVars → IGCC 태그 dict (10개 필드)."""
    return {
        TAG_SYNGAS_FLOW: vars.syngas_flow,
        TAG_IGV_OPENING: vars.igv_opening,
        TAG_N2_OFFSET: vars.n2_offset,
        TAG_N2_VALVE_1: vars.n2_valve_1,
        TAG_SYNGAS_SRV: vars.syngas_srv,
        TAG_SYNGAS_GCV_1: vars.syngas_gcv_1,
        TAG_SYNGAS_GCV_1A: vars.syngas_gcv_1a,
        TAG_SYNGAS_GCV_2: vars.syngas_gcv_2,
        TAG_IBH_VALVE: vars.ibh_valve,
        TAG_N2_FLOW: vars.n2_flow,
    }


# ============================================================
# 변수별 운영 한계 (기본값) — [추후 결정]
# 신규 7개 변수의 한계는 가안 임의값. 데이터 분포 확보 후 재산정 필요.
# 프론트의 ▲▼ 버튼 한계 도달 비활성화 로직과 일치시킨다.
# ============================================================
@dataclass(frozen=True)
class ControlBounds:
    syngas_flow_min: float = 800.0
    syngas_flow_max: float = 2200.0
    igv_opening_min: float = 30.0
    igv_opening_max: float = 100.0
    n2_offset_min: float = 0.0
    n2_offset_max: float = 500.0
    # 신규 7개 — 개도 변수는 [0, 100], n2_flow는 [0, 500] 가안
    n2_valve_1_min: float = 0.0
    n2_valve_1_max: float = 100.0
    syngas_srv_min: float = 0.0
    syngas_srv_max: float = 100.0
    syngas_gcv_1_min: float = 0.0
    syngas_gcv_1_max: float = 100.0
    syngas_gcv_1a_min: float = 0.0
    syngas_gcv_1a_max: float = 100.0
    syngas_gcv_2_min: float = 0.0
    syngas_gcv_2_max: float = 100.0
    ibh_valve_min: float = 0.0
    ibh_valve_max: float = 100.0
    n2_flow_min: float = 0.0
    n2_flow_max: float = 500.0


DEFAULT_CONTROL_BOUNDS: Final[ControlBounds] = ControlBounds()


# ControlVars 필드명 ↔ 태그 ↔ ControlBounds 한계 매핑.
# validate_control이 데이터 주도형으로 동작하도록 모듈 상단에 선언.
_FIELD_RULES: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("syngas_flow", TAG_SYNGAS_FLOW, "syngas_flow_min", "syngas_flow_max"),
    ("igv_opening", TAG_IGV_OPENING, "igv_opening_min", "igv_opening_max"),
    ("n2_offset", TAG_N2_OFFSET, "n2_offset_min", "n2_offset_max"),
    ("n2_valve_1", TAG_N2_VALVE_1, "n2_valve_1_min", "n2_valve_1_max"),
    ("syngas_srv", TAG_SYNGAS_SRV, "syngas_srv_min", "syngas_srv_max"),
    ("syngas_gcv_1", TAG_SYNGAS_GCV_1, "syngas_gcv_1_min", "syngas_gcv_1_max"),
    ("syngas_gcv_1a", TAG_SYNGAS_GCV_1A, "syngas_gcv_1a_min", "syngas_gcv_1a_max"),
    ("syngas_gcv_2", TAG_SYNGAS_GCV_2, "syngas_gcv_2_min", "syngas_gcv_2_max"),
    ("ibh_valve", TAG_IBH_VALVE, "ibh_valve_min", "ibh_valve_max"),
    ("n2_flow", TAG_N2_FLOW, "n2_flow_min", "n2_flow_max"),
)


def validate_control(
    vars: ControlVars, bounds: ControlBounds = DEFAULT_CONTROL_BOUNDS
) -> list[str]:
    """범위를 벗어난 값에 대한 에러 메시지 목록을 반환. 빈 리스트면 정상."""
    errors: list[str] = []
    for field, tag, min_attr, max_attr in _FIELD_RULES:
        value = getattr(vars, field)
        lo = getattr(bounds, min_attr)
        hi = getattr(bounds, max_attr)
        if not (lo <= value <= hi):
            errors.append(f"{tag}={value} out of range [{lo}, {hi}]")
    return errors
