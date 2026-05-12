from fastapi import APIRouter, Depends

from app.api.deps import get_kafka_sensor_stream
from app.core.kafka_stream import KafkaSensorStream
from app.schemas.streaming import StreamingLatestResponse

router = APIRouter(prefix="/streaming", tags=["streaming"])


@router.get("/latest", response_model=StreamingLatestResponse)
def latest_stream_message(
    stream: KafkaSensorStream = Depends(get_kafka_sensor_stream),
) -> StreamingLatestResponse:
    return StreamingLatestResponse(
        enabled=stream.enabled,
        topic=stream.topic,
        latest=stream.latest,
        last_error=stream.last_error,
    )
