import pandas as pd
from app.core.sensor_buffer import SensorBuffer


def test_empty_buffer():
    buf = SensorBuffer(maxlen=900)
    assert len(buf) == 0
    assert buf.latest_row() is None


def test_append_and_latest():
    buf = SensorBuffer(maxlen=3)
    buf.append({"syngas_flow": 100.0})
    buf.append({"syngas_flow": 101.0})
    assert len(buf) == 2
    assert buf.latest_row() == {"syngas_flow": 101.0}


def test_maxlen_evicts_oldest():
    buf = SensorBuffer(maxlen=2)
    buf.append({"v": 1})
    buf.append({"v": 2})
    buf.append({"v": 3})
    assert len(buf) == 2
    assert buf.latest_row() == {"v": 3}
    df = buf.to_dataframe()
    assert df["v"].tolist() == [2, 3]


def test_load_bootstrap_overwrites():
    buf = SensorBuffer(maxlen=900)
    rows = [{"syngas_flow": float(i)} for i in range(5)]
    buf.load_bootstrap(rows)
    assert len(buf) == 5
    assert buf.latest_row() == {"syngas_flow": 4.0}


def test_to_dataframe_columns():
    buf = SensorBuffer(maxlen=5)
    buf.append({"a": 1.0, "b": 2.0})
    buf.append({"a": 3.0, "b": 4.0})
    df = buf.to_dataframe()
    assert list(df.columns) == ["a", "b"]
    assert df.shape == (2, 2)
