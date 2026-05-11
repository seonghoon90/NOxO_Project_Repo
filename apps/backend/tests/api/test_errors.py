from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.errors import register_exception_handlers
from app.exceptions import DataNotEnoughError, DataSourceUnavailableError


def test_data_not_enough_error_maps_to_503():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise")
    def raise_error():
        raise DataNotEnoughError("not enough rows")

    res = TestClient(app).get("/raise")

    assert res.status_code == 503
    assert res.json()["error_code"] == "DATA_NOT_ENOUGH"


def test_data_source_unavailable_error_maps_to_503():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise")
    def raise_error():
        raise DataSourceUnavailableError("db unavailable")

    res = TestClient(app).get("/raise")

    assert res.status_code == 503
    assert res.json()["error_code"] == "DATA_SOURCE_UNAVAILABLE"
