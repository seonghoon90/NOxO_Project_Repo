"""5분 뒤 NOx 예측 CLI.

학습된 모델로 CSV 입력에서 5분 뒤 NOx를 예측한다.

사용법:
    # 단일 예측 (마지막 15분으로 한 번)
    python -m digital_twin.forecaster.cli predict --data path/to/recent.csv

    # 전체 시계열 평가 (학습/테스트 CSV에서 매 행 예측)
    python -m digital_twin.forecaster.cli evaluate --data path/to/test.csv

    # 모델 정보 출력
    python -m digital_twin.forecaster.cli info
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from digital_twin.forecaster.predict import (
    DEFAULT_META_PATH,
    DEFAULT_MODEL_PATH,
    load_model,
    predict,
)
from digital_twin.forecaster.preprocess import (
    EXTENDED_FEATURES,
    FEATURES,
    GENERIC_FEATURES,
    NOX_LAG_FEATURES,
    NOX_TARGET_COL,
    TARGET_COL,
    add_extended_features,
    add_generic_features,
    add_interaction_features,
    add_nox_lag_features,
    add_time_features,
    load_data,
    make_forecast_target_1s,
)


def _cmd_info(args) -> None:
    """모델 메타데이터 출력."""
    mp = Path(args.model) if args.model else DEFAULT_MODEL_PATH
    metap = Path(args.metadata) if args.metadata else DEFAULT_META_PATH
    if not mp.exists() or not metap.exists():
        print(f"❌ 모델 파일 없음: {mp}\n먼저 학습 필요: python -m digital_twin.forecaster.train --data <csv>")
        sys.exit(1)
    meta = json.loads(metap.read_text(encoding="utf-8"))
    print(f"📦 Forecaster 모델 정보")
    print(f"  경로         : {mp}")
    print(f"  종류         : {meta.get('model_type')}")
    print(f"  horizon      : {meta.get('horizon_minutes')}분 (= {meta.get('horizon_seconds')}초)")
    print(f"  피처 개수    : {meta.get('n_features')}")
    print(f"  train 샘플   : {meta.get('n_train'):,}")
    print(f"  val 샘플     : {meta.get('n_val'):,}")
    print(f"  학습 시각    : {meta.get('trained_at')}")
    print(f"  ensemble w   : {meta.get('ensemble_w_ridge')} (Ridge)")
    tm = meta.get("train_metrics", {})
    vm = meta.get("val_metrics", {})
    print(f"  train R²     : {tm.get('r2'):.4f}  MAE {tm.get('mae'):.4f}  RMSE {tm.get('rmse'):.4f}")
    print(f"  val   R²     : {vm.get('r2'):.4f}  MAE {vm.get('mae'):.4f}  RMSE {vm.get('rmse'):.4f}")


def _cmd_predict(args) -> None:
    """CSV에서 단일 5분 뒤 NOx 예측 (마지막 15분 window 기준)."""
    loaded = load_model(args.model, args.metadata)
    df, _ = load_data(args.data, npr_hinge_threshold=loaded.npr_threshold)
    # 마지막 N분 사용
    n_rows = max(900, args.window_seconds)
    recent = df.tail(n_rows)
    if len(recent) < 900:
        print(f"⚠️  입력 길이 부족: {len(recent)}행 (권장 ≥900). 폴백 동작.")
    pred = predict(loaded, recent_df=recent)
    nox_now = float(recent[NOX_TARGET_COL].iloc[-1]) if NOX_TARGET_COL in recent.columns else None

    result = {
        "predicted_nox_5min_later": round(pred, 4),
        "current_nox": round(nox_now, 4) if nox_now is not None else None,
        "delta": round(pred - nox_now, 4) if nox_now is not None else None,
        "input_rows": len(recent),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


def _cmd_evaluate(args) -> None:
    """CSV 전체에서 매 행 예측 vs 실측 비교."""
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    loaded = load_model(args.model, args.metadata)
    df, _ = load_data(args.data, npr_hinge_threshold=loaded.npr_threshold)
    df = add_nox_lag_features(df)
    df = add_extended_features(df)
    df = add_generic_features(df)
    df = add_interaction_features(df)
    df = add_time_features(df)
    df = df.dropna(subset=NOX_LAG_FEATURES + EXTENDED_FEATURES + GENERIC_FEATURES)
    df_tgt = make_forecast_target_1s(df)

    X = df_tgt[FEATURES]
    y = df_tgt[TARGET_COL].values
    nox_now = df_tgt[NOX_TARGET_COL].values

    y_pred = loaded.model.predict(X)
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    r2 = r2_score(y, y_pred)
    persist_r2 = r2_score(y, nox_now)

    print(f"📊 평가 결과 ({args.data})")
    print(f"  샘플 수        : {len(y):,}")
    print(f"  NOx 분포       : min={y.min():.2f}, max={y.max():.2f}, mean={y.mean():.2f}, std={y.std():.4f}")
    print(f"  ──── 모델 ────")
    print(f"  MAE            : {mae:.4f} ppm")
    print(f"  RMSE           : {rmse:.4f} ppm")
    print(f"  R²             : {r2:.4f}")
    print(f"  ──── Persistence baseline ────")
    print(f"  R²             : {persist_r2:.4f}")
    print(f"  ──── 개선 ────")
    print(f"  R² +{r2 - persist_r2:.4f}")

    if args.output:
        out_df = pd.DataFrame({
            "current_nox": nox_now,
            "actual_5min_later": y,
            "predicted_5min_later": y_pred,
            "error": y_pred - y,
        })
        out_df.to_csv(args.output, index=False, encoding="utf-8-sig")
        print(f"\n📁 결과 CSV: {args.output}")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="forecaster",
        description="5분 뒤 NOx 예측 CLI",
    )
    sub = p.add_subparsers(dest="command", required=True)

    p_info = sub.add_parser("info", help="모델 메타데이터 출력")
    p_info.add_argument("--model", default=None)
    p_info.add_argument("--metadata", default=None)
    p_info.set_defaults(func=_cmd_info)

    p_pred = sub.add_parser("predict", help="단일 5분 뒤 NOx 예측")
    p_pred.add_argument("--data", required=True, help="입력 CSV (1초 raw)")
    p_pred.add_argument("--window-seconds", type=int, default=900, help="사용할 마지막 N초 (기본 900=15분)")
    p_pred.add_argument("--model", default=None)
    p_pred.add_argument("--metadata", default=None)
    p_pred.set_defaults(func=_cmd_predict)

    p_eval = sub.add_parser("evaluate", help="CSV 전체에서 매 행 평가")
    p_eval.add_argument("--data", required=True, help="평가용 CSV")
    p_eval.add_argument("--output", default=None, help="결과 CSV 저장 경로 (선택)")
    p_eval.add_argument("--model", default=None)
    p_eval.add_argument("--metadata", default=None)
    p_eval.set_defaults(func=_cmd_evaluate)

    return p


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
