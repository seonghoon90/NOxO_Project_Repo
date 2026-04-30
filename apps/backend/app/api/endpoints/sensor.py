from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_sensor_service
from app.domain.sensor import SensorReading
from app.schemas.sensor import SensorPayload
from app.services.sensor_service import SensorService

router = APIRouter(prefix="/sensor", tags=["sensor"])


def _to_payload(r: SensorReading) -> SensorPayload:
    return SensorPayload(
        measured_at=r.measured_at,
        nox_ppm=r.nox_ppm,
        dgan_offset=r.dgan_offset,
        syngas_flow=r.syngas_flow,
        generator_output=r.generator_output,
        npr_primary=r.npr_primary,
        ambient_temp=r.ambient_temp,
        dgan_flow=r.dgan_flow,
        igv=r.igv,
    )


@router.get("/latest", response_model=SensorPayload)
def latest(
    service: Annotated[SensorService, Depends(get_sensor_service)],
) -> SensorPayload:
    return _to_payload(service.latest())


@router.get("/history", response_model=list[SensorPayload])
def history(
    service: Annotated[SensorService, Depends(get_sensor_service)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[SensorPayload]:
    return [_to_payload(r) for r in service.history(limit=limit, offset=offset)]
