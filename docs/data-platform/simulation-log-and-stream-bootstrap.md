# Simulation Log And Stream Bootstrap

## 1. What was implemented

The backend now writes the simulation / forecast log tables defined in the DB docs.

- `simulation_session_log`
- `simulation_input_log`
- `forecast_log`

The write path is best-effort.

- If DB logging is available, the backend writes the records.
- If DB connection or table creation fails, session and prediction APIs still work.
- This was intentional so local tests and non-DB runtime do not break the service.

## 2. Backend hook points

The current write flow is:

1. `POST /api/session/start`
   - create `simulation_session_log`
   - create first `simulation_input_log`
2. `POST /api/session/{sid}/control`
   - create `simulation_input_log`
3. `POST /api/session/{sid}/stop`
   - update `simulation_session_log.ended_at`
4. `POST /api/prediction`
   - create `forecast_log`

Main files:

- `apps/backend/app/repositories/simulation_log_repo.py`
- `apps/backend/app/services/session_service.py`
- `apps/backend/app/services/forecast_service.py`
- `apps/backend/app/core/lifespan.py`
- `apps/backend/app/api/deps.py`

## 3. Table creation behavior

On app startup, if DB config exists, the backend tries to create the log tables with `CREATE TABLE IF NOT EXISTS`.

If that step fails:

- warning log only
- `simulation_log_repo` becomes `None`
- the rest of the backend keeps running

This avoids blocking:

- local test runs
- Docker test runs
- app startup when DB is temporarily unreachable

## 4. Validation

Validated with Docker-based backend tests.

- `test_session_service.py`
- `test_forecast_service.py`
- `test_simulation_log_flow.py`
- `test_session_flow.py`

Result:

- `14 passed`

## 5. Current meaning of each table

### `simulation_session_log`

One row per simulation session.

- `sid`
- `started_at`
- `ended_at`
- `notes`

### `simulation_input_log`

One row per input state injection.

- initial control snapshot on session start
- every control update from frontend or API

### `forecast_log`

One row per prediction request.

- optional `sid`
- prediction creation time
- target forecast time
- predicted NOx
- threshold value
- threshold exceeded flag

## 6. Discussion item: preload 15 minutes, then switch to live Kafka

Yes, this is implementable.

Recommended flow:

1. Service starts
2. Backend loads the first 15 minutes of `NOx_test_20250825.csv`
3. Backend exposes those rows immediately to frontend
4. Kafka producer starts from the next timestamp after that preload window
5. Frontend first renders preload data, then continues with live stream updates

## 7. Recommended implementation shape

### Option A. Backend-owned bootstrap state

Backend loads preload rows into memory on startup and exposes:

- `GET /api/streaming/bootstrap`
- `GET /api/streaming/latest`

Suggested behavior:

- `/api/streaming/bootstrap` returns the initial 15-minute dataset
- `/api/streaming/latest` returns the most recent Kafka-consumed row

Pros:

- frontend stays simple
- bootstrap and live stream contract stays in one backend layer
- easiest for team handoff

### Option B. Frontend loads CSV-derived data separately

Frontend calls one preload API and then switches to another live API.

This is also possible, but backend should still own the CSV slicing logic.

## 8. Recommended contract

For this project, the cleanest next contract is:

1. `GET /api/streaming/bootstrap?minutes=15`
2. `GET /api/streaming/latest`

Optional next step later:

3. `GET /api/streaming/window`
   - recent N rows
4. WebSocket or SSE stream

## 9. Producer behavior for the preload design

If we adopt the 15-minute preload strategy, the producer should not start from `00:00:00`.

It should:

1. skip the first 15 minutes already shown by the backend
2. begin publishing from the next row after the preload boundary

That avoids duplicate rendering on the frontend.

## 10. Team note

This design is suitable for demo and portfolio flow because:

- users see immediate data on first screen load
- no empty dashboard waiting for Kafka
- the transition from historical bootstrap to live simulation is easy to explain
- DB log tables can later store session/prediction history alongside the stream
