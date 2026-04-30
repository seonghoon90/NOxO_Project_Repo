#!/usr/bin/env python3
"""
베이스라인 분석 문서를 바탕으로 synthetic 데이터 생성
실제 데이터 특성:
  - 1,296,000행, 88개 피처
  - NOx 평균 29.28 ± 0.19 ppm
  - 시계열 데이터 (1초 간격)
"""

import numpy as np
import pandas as pd
from pathlib import Path

def generate_synthetic_data(n_samples=10000, n_features=88, seed=42):
    """
    베이스라인 분석 특성을 반영한 합성 데이터 생성
    """
    np.random.seed(seed)

    print(f"📊 생성 중: {n_samples:,}행 × {n_features}개 피처")

    # 1. 피처 생성 (온도, 압력, 출력, N2 제어 등)
    X = np.random.randn(n_samples, n_features) * 10 + 100

    # 2. 피처 이름 (베이스라인 문서 기반)
    feature_names = [
        # 온도 관련 (4개)
        'TTXM', 'CTIM', 'CTD', 'ATID',
        # 압력 관련 (3개)
        'VNPR_P', 'VNPR_S', 'CPD',
        # N2 제어 (3개)
        'NQJ', 'nicvs1', 'NPNJ',
        # 연료 (2개)
        'ca_fqsg_cl', 'LHVSYNDW_SCF',
        # DeNOx (2개)
        'AIT_H1_902', 'TT_H1_90123',
        # 출력 (1개)
        'DWATT',
    ] + [f'Feature_{i:02d}' for i in range(15, n_features)]

    # 3. 타깃 변수 생성 (NOx)
    # 베이스라인: 평균 29.28, 표준편차 0.19, 범위 27.75~30.41
    y = np.random.normal(29.28, 0.19, n_samples)
    y = np.clip(y, 27.75, 30.41)

    # 피처와 타깃 간의 약한 상관관계 추가 (현실성)
    y += X[:, 0] * 0.01  # TTXM과 약한 상관
    y += X[:, 7] * 0.005  # NQJ와 약한 상관

    # 4. DataFrame 생성
    X_df = pd.DataFrame(X, columns=feature_names)
    df = pd.concat([X_df, pd.DataFrame({'IGCC.DeNOX.AT_H1_901_PV': y})], axis=1)

    print(f"✅ 데이터 생성 완료")
    print(f"   - Shape: {df.shape}")
    print(f"   - Target mean: {y.mean():.2f} (Baseline: 29.28)")
    print(f"   - Target std: {y.std():.4f} (Baseline: 0.19)")

    return df, feature_names

if __name__ == '__main__':
    # 데이터 생성
    df, feature_names = generate_synthetic_data(n_samples=10000)

    # 저장
    output_dir = Path('../../data') / 'synthetic'
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / 'synthetic_data.parquet'
    df.to_parquet(output_path, index=False)

    print(f"💾 저장 완료: {output_path}")
