"""제어 변수 / 출력 변수 태그 정의.

프론트엔드와 백엔드가 공유하는 식별자. 추후 `[DB 협의 필요]`로 컬럼명이
확정되면 본 모듈을 단일 진입점으로 사용하여 매핑한다.
"""

from dataclasses import dataclass
from typing import Final


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


@dataclass(frozen=True)
class ControlVars:
    """제어 입력 도메인 모델 — 단일 step에 적용될 목표값."""

    syngas_flow: float        # IGCC.CC.G1.ca_fqsg_cl
    n2_offset: float          # IGCC.CC.G1.NQKR3_MONITOR
    igv_opening: float        # IGCC.CC.G1.csgv

    @classmethod
    def from_tag_dict(cls, tags: dict[str, float]) -> "ControlVars":
        return cls(
            syngas_flow=tags[TAG_SYNGAS_FLOW],
            n2_offset=tags[TAG_N2_OFFSET],
            igv_opening=tags[TAG_IGV_OPENING],
        )

    def to_tag_dict(self) -> dict[str, float]:
        return {
            TAG_SYNGAS_FLOW: self.syngas_flow,
            TAG_N2_OFFSET: self.n2_offset,
            TAG_IGV_OPENING: self.igv_opening,
        }


# ============================================================
# 출력 변수 (백엔드 → 프론트, WebSocket)
# ============================================================
TAG_POWER: Final[str] = "IGCC.CC.G1.DWATT"  # 발전량 (MW)


@dataclass(frozen=True)
class OutputVars:
    """모델 추론 결과 — 단위는 [추후 결정]."""

    nox: float            # ppm (가안)
    co: float             # ppm (가안)
    flame_temp: float     # K (가안)
    lambda_: float        # 공기비 (dimensionless)
    power: float          # MW — IGCC.CC.G1.DWATT


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


def validate_control(vars: ControlVars, bounds: ControlBounds = DEFAULT_CONTROL_BOUNDS) -> list[str]:
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
