# Kafka API Handoff

프론트엔드/백엔드 담당자가 같은 기준으로 작업할 수 있도록 Kafka streaming API의 현재 계약을 정리한다.

## Current Status

- Kafka streaming 코드는 `dev`에 merge 완료
- 로컬 Docker 기준 검증 완료
- 검증 범위
  - Redpanda broker 실행
  - Producer가 `NOx_test_20250825.csv` 5건 발행
  - backend consumer가 topic 구독
  - `GET /api/streaming/latest` 응답 확인
- App EC2에서는 아직 Kafka streaming 전체를 별도 실검증하지 않음

## Purpose

이 API는 두 단계로 나뉜다.

- bootstrap: 서비스 진입 직후 보여줄 초기 15분 데이터
- latest: Kafka topic에 들어온 최신 센서 메시지 1건

백엔드는 preload와 live stream 사이의 경계를 관리하고, 프론트는 그 계약에 맞춰 바로 렌더링할 수 있다.

현재 목적은 다음과 같다.

- Kafka/Redpanda 기반 실시간 데이터 흐름을 팀 구조에 맞게 노출
- 프론트가 우선 polling 방식으로 빠르게 연결 가능하도록 지원
- 이후 WebSocket 통합 전까지 임시가 아닌 명시적 latest endpoint 제공

## Endpoints

- Method: `GET`
- Path: `/api/streaming/bootstrap`

예시:

```text
GET /api/streaming/bootstrap
```

- Method: `GET`
- Path: `/api/streaming/latest`

예시:

```text
GET /api/streaming/latest
```

## Bootstrap Response Shape

```json
{
  "enabled": true,
  "topic": "noxo.sensor.raw",
  "minutes": 15,
  "count": 900,
  "source": "NOx_test_20250825.csv",
  "rows": [
    {
      "source": "NOx_test_20250825.csv",
      "measured_at": "2025-08-25 00:00:04",
      "values": {
        "IGCC.CC.G1.csgv": 62.58331
      }
    }
  ],
  "error": null
}
```

## Latest Response Shape

consumer가 꺼져 있거나 아직 메시지를 받지 못한 경우:

```json
{
  "enabled": true,
  "topic": "noxo.sensor.raw",
  "latest": null,
  "last_error": null
}
```

최신 메시지를 받은 경우:

```json
{
  "enabled": true,
  "topic": "noxo.sensor.raw",
  "latest": {
    "topic": "noxo.sensor.raw",
    "partition": 0,
    "offset": 9,
    "key": "2025-08-25 00:00:04",
    "received_at": "2026-05-12T00:27:34Z",
    "message": {
      "source": "NOx_test_20250825.csv",
      "measured_at": "2025-08-25 00:00:04",
      "published_at": "2026-05-12T00:27:34Z",
      "values": {
        "IGCC.CC.G1.csgv": 62.58331,
        "IGCC.CC.G1.DWATT": 162.9748,
        "IGCC.DeNOX.AT_H1_901_PV": 29.19837
      }
    }
  },
  "last_error": null
}
```

## Important Notes

- `/api/streaming/bootstrap`은 초기 preload 구간을 반환한다.
- producer는 bootstrap 구간 이후의 row부터 Kafka로 발행한다.
- 이 endpoint는 배열이 아니라 latest 단일 객체를 반환한다.
- `latest.message.values`에는 원천 센서 태그명이 그대로 들어간다.
- `Column1` 같은 보조 빈 컬럼은 producer 단계에서 제외한다.
- `key`는 현재 `measured_at`과 동일한 값이다.
- `last_error`가 null이 아니면 consumer 연결 또는 브로커 접근 문제를 의심한다.

## Frontend Guide

프론트는 다음 순서로 붙이는 것이 가장 단순하다.

- 최초 진입 시 `/api/streaming/bootstrap` 호출
- 그 다음 1초 또는 2초 간격으로 `/api/streaming/latest` 호출
- `latest === null`이면 "대기 중" 상태 처리
- `latest.message.values`에서 필요한 태그만 골라 UI에 매핑
- 향후 WebSocket 통합 시 same source of truth를 재정리

## Backend Guide

백엔드는 환경변수로 consumer를 켠다.

- `KAFKA_STREAM_ENABLED=true`
- `KAFKA_BOOTSTRAP_SERVERS=redpanda:9092`
- `KAFKA_SENSOR_TOPIC=noxo.sensor.raw`
- `KAFKA_CONSUMER_GROUP_ID=noxo-backend-stream`
- `KAFKA_BOOTSTRAP_MINUTES=15`
- `KAFKA_BOOTSTRAP_FILE=/app/data/raw/250811-250825/NOx_test_20250825.csv`

현재 backend는 preload rows와 latest 1건을 메모리에 유지한다.

## Source Files

- API endpoint: `apps/backend/app/api/endpoints/streaming.py`
- consumer: `apps/backend/app/core/kafka_stream.py`
- response schema: `apps/backend/app/schemas/streaming.py`
- producer: `streaming/producer.py`
- compose: `docker/docker-compose.kafka.yml`

## Next Team Step

- 프론트는 `bootstrap -> latest polling` 순서로 연결 시작
- 백엔드는 App EC2에서 preload + consumer 실배포 검증
- 이후 필요하면 WebSocket 통합 여부를 별도 결정
