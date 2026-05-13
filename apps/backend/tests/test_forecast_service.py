from datetime import datetime, timezone

from app.adapters.forecaster import StubForecaster
from app.services.forecast_service import ForecastService


class _FakeSimulationLogRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str | None, float, bool]] = []

    def create_forecast_log(self, response, sid: str | None = None) -> None:
        self.calls.append((sid, response.predicted_nox, response.threshold_exceeded))


def test_predict_logs_forecast():
    repo = _FakeSimulationLogRepo()
    service = ForecastService(
        sessions={},
        forecaster=StubForecaster(),
        simulation_log_repo=repo,
    )

    response = service.predict()

    assert isinstance(response.target_time, datetime)
    assert response.target_time.tzinfo == timezone.utc
    assert repo.calls == [(None, response.predicted_nox, response.threshold_exceeded)]
