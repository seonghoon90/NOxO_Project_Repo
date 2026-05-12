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
# 출력/관측 태그 — ERD sensor_data 출력 컬럼
# 도메인 키 = OutputVars 필드명 (DB ERD 컬럼명과 별개)
#   ERD nox_ppm/power_mw → 도메인 nox/power
# ============================================================
TAG_NOX_PPM: Final[str] = "IGCC.DeNOX.AT_H1_901_PV"   # TODO: 실제 NOx 측정 태그 확인 (가안)
TAG_EXHAUST_TEMP: Final[str] = "IGCC.CC.G1.TTXM"
# TAG_NPR_PRIMARY: TODO — IGCC.CC.G1.NQJ는 이미 TAG_N2_FLOW(=n2_flow)에 할당됨.
#                  실제 NPR primary 측정 태그를 확인 후 추가할 것.
# TAG_POWER는 기존 정의(L51) 사용 → "IGCC.CC.G1.DWATT"


# ============================================================
# 외란 29개 — TODO: 모델링 팀과 매핑 검토 (후속 작업)
# 외란 매핑이 미완이어도 시스템은 동작 (DT 모델이 ffill 폴백 경로로 작동)
# ============================================================
DISTURBANCE_TAGS: Final[dict[str, str]] = {
    # 예시 (실제 매핑은 후속 작업):
    # "IGCC.CC.G1.PCD": "compressor_discharge_pressure",
    # 추후 digital_twin/preprocess.RAW_FEATURES 39개에서
    # CONTROL_TAGS 10개 + 출력 5개를 뺀 24개에 임의 도메인명 부여
}


# ============================================================
# 통합 매핑 — Kafka 메시지 정규화용
# ============================================================
ALL_TAGS_TO_DOMAIN: Final[dict[str, str]] = {
    # 제어 10개
    TAG_SYNGAS_FLOW: "syngas_flow",
    TAG_IGV_OPENING: "igv_opening",
    TAG_N2_OFFSET: "n2_offset",
    TAG_N2_VALVE_1: "n2_valve_1",
    TAG_SYNGAS_SRV: "syngas_srv",
    TAG_SYNGAS_GCV_1: "syngas_gcv_1",
    TAG_SYNGAS_GCV_1A: "syngas_gcv_1a",
    TAG_SYNGAS_GCV_2: "syngas_gcv_2",
    TAG_IBH_VALVE: "ibh_valve",
    TAG_N2_FLOW: "n2_flow",
    # 출력 3개 (npr_primary는 NQJ 충돌로 보류, TODO 참조)
    TAG_NOX_PPM: "nox",
    TAG_EXHAUST_TEMP: "exhaust_temp",
    TAG_POWER: "power",
    # 외란
    **DISTURBANCE_TAGS,
}


def normalize_raw_message(values: dict[str, float]) -> dict[str, float]:
    """Kafka 메시지의 values dict (원천 태그명) → 도메인 snake_case dict.

    매핑 외 키는 dropped. 외란 매핑 미완 단계에서는 ERD 13개(제어 10 + 출력 3)만
    반환된다 (npr_primary는 NQJ 키 충돌로 추후 추가 예정).
    """
    return {
        ALL_TAGS_TO_DOMAIN[k]: v
        for k, v in values.items()
        if k in ALL_TAGS_TO_DOMAIN
    }


# ============================================================
# 도메인 → 원천 태그 역매핑 (SessionContext 재구성용)
# ============================================================
DOMAIN_TO_RAW_TAG: Final[dict[str, str]] = {
    v: k for k, v in ALL_TAGS_TO_DOMAIN.items()
}


def denormalize_to_raw_tags(domain_dict: dict[str, float]) -> dict[str, float]:
    """도메인 snake_case dict → 원천 태그 dict (SessionContext 호환용)."""
    return {
        DOMAIN_TO_RAW_TAG[k]: v
        for k, v in domain_dict.items()
        if k in DOMAIN_TO_RAW_TAG
    }


def control_payload_to_controlvars(payload) -> ControlVars:
    """ControlPayload → ControlVars (도메인 객체로 변환)."""
    return ControlVars(
        syngas_flow=payload.syngas_flow, igv_opening=payload.igv_opening,
        n2_offset=payload.n2_offset, n2_valve_1=payload.n2_valve_1,
        syngas_srv=payload.syngas_srv, syngas_gcv_1=payload.syngas_gcv_1,
        syngas_gcv_1a=payload.syngas_gcv_1a, syngas_gcv_2=payload.syngas_gcv_2,
        ibh_valve=payload.ibh_valve, n2_flow=payload.n2_flow,
    )


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
