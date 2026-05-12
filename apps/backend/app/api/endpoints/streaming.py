from fastapi import APIRouter, Depends

from app.api.deps import get_kafka_sensor_stream
from app.core.kafka_stream import KafkaSensorStream
from app.schemas.streaming import StreamingBootstrapResponse, StreamingLatestResponse

router = APIRouter(prefix="/streaming", tags=["streaming"])


@router.get("/bootstrap", response_model=StreamingBootstrapResponse)
def bootstrap_stream_messages(
    stream: KafkaSensorStream = Depends(get_kafka_sensor_stream),
) -> StreamingBootstrapResponse:
    return StreamingBootstrapResponse(
        enabled=stream.enabled,
        topic=stream.topic,
        minutes=stream.bootstrap_minutes,
        count=len(stream.bootstrap_rows),
        source=stream.bootstrap_source,
        rows=stream.bootstrap_rows,
        error=stream.bootstrap_error,
    )


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
