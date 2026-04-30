# 실험 추적 & 결과 관리 가이드

> **목적**: AI 엔지니어가 수십 개의 실험을 체계적으로 기록하고 비교할 수 있는 방법
> **작성일**: 2026-04-30

---

## 🎯 실험 추적이 필요한 이유

### 문제 상황
```
❌ 나쁜 예:
- 모델 여러 개 만들었는데 어떤 게 최고 성능인지 기억 안 남
- 3주 전에 0.088 MAE가 나온 설정이 뭐였는지 모름
- "그 때 추가했던 피처가 뭐였더라?"
- 실험 결과 엑셀 파일에 손으로 수작업 입력 → 실수 많음
```

### 해결책
```
✅ 좋은 예:
- 모든 실험은 JSON으로 자동 저장
- 검색/필터링으로 top 5 모델 1초 안에 찾음
- 실험 설정 재현 가능 (코드 + 설정파일 + 메타데이터 함께 저장)
- Python으로 자동 분석 (Pandas로 표/그래프 생성)
```

---

## 📁 실험 추적 폴더 구조

```
analysis/Engineering/
├── experiments/
│   ├── metadata/                    ← 모든 실험의 메타데이터
│   │   ├── exp_001_ridge_baseline.json
│   │   ├── exp_002_xgboost_baseline.json
│   │   ├── exp_003_lightgbm_v1.json
│   │   ├── exp_004_lightgbm_v2.json (하이퍼파라미터 튜닝)
│   │   └── exp_005_tabnet_v1.json
│   │
│   ├── models/                      ← 학습된 모델 파일
│   │   ├── exp_001_model.pkl
│   │   ├── exp_002_model.pkl
│   │   └── exp_003_model.pkl
│   │
│   ├── logs/                        ← 학습 로그
│   │   ├── exp_001_train.log
│   │   ├── exp_002_train.log
│   │   └── exp_003_train.log
│   │
│   └── results_summary.csv          ← 자동 생성되는 비교표
```

---

## 📋 실험 메타데이터 형식

### 기본 구조

```json
{
  "experiment_id": "exp_003_lightgbm_v1",
  "timestamp": "2026-04-30T14:32:00",
  "status": "completed",
  
  "model_info": {
    "type": "LightGBM",
    "config_file": "configs/exp_lightgbm_v1.yaml",
    "framework": "lightgbm",
    "version": "4.0.0"
  },
  
  "data_info": {
    "train_size": 1_036_800,
    "val_size": 259_200,
    "test_size": 0,
    "n_features": 88,
    "feature_selection": "all_features",
    "target_variable": "IGCC.DeNOX.AT_H1_901_PV",
    "notes": "O₂ 포함, Interaction 피처 추가"
  },
  
  "performance": {
    "train_mae": 0.0847,
    "train_rmse": 0.1089,
    "val_mae": 0.0912,
    "val_rmse": 0.1156,
    "test_mae": 0.0988,
    "test_rmse": 0.1234
  },
  
  "training": {
    "epochs": 450,
    "early_stopping_round": 50,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "lambda_l1": 0.0,
    "lambda_l2": 0.1
  },
  
  "insights": {
    "top_5_features": [
      {"name": "TTXM", "importance": 0.245},
      {"name": "DWATT", "importance": 0.189},
      {"name": "CTIM", "importance": 0.156},
      {"name": "CPD", "importance": 0.121},
      {"name": "VNPR_P", "importance": 0.089}
    ],
    "key_finding": "온도(TTXM)가 가장 중요. 부하(DWATT)와의 interaction 효과 관찰",
    "potential_improvements": [
      "Early stopping round을 30으로 줄이면 오버피팅 가능성 감소",
      "num_leaves를 16으로 줄여서 정규화 강화 필요"
    ]
  },
  
  "comparison": {
    "vs_baseline_ridge": "+3.2% 개선 (MAE 0.095 → 0.092)",
    "vs_baseline_xgboost": "-0.5% 악화 (MAE 0.089 → 0.092)"
  },
  
  "artifacts": {
    "model_file": "experiments/models/exp_003_model.pkl",
    "model_size_mb": 28.4,
    "log_file": "experiments/logs/exp_003_train.log",
    "config_file": "configs/exp_lightgbm_v1.yaml"
  },
  
  "notes": "XGBoost와 비슷한 성능이지만 학습이 30% 빠름. 다음은 하이퍼파라미터 튜닝 시도.",
  "author": "AI Engineer",
  "tags": ["baseline_comparison", "lightgbm_exploration"]
}
```

---

## 🔧 자동화: Python 실험 추적 스크립트

### scripts/experiment_tracker.py

```python
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
import uuid

class ExperimentTracker:
    def __init__(self, experiments_dir: str = "experiments"):
        self.experiments_dir = Path(experiments_dir)
        self.metadata_dir = self.experiments_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def start_experiment(self, 
                        model_type: str,
                        config_file: str,
                        description: str = "") -> str:
        """새 실험 시작"""
        # 실험 ID 생성 (exp_001, exp_002, ...)
        existing = list(self.metadata_dir.glob("exp_*.json"))
        exp_num = len(existing) + 1
        exp_id = f"exp_{exp_num:03d}_{model_type.lower()}"
        
        self.current_exp = {
            "experiment_id": exp_id,
            "timestamp": datetime.now().isoformat(),
            "status": "in_progress",
            "model_info": {
                "type": model_type,
                "config_file": config_file,
            },
            "description": description,
        }
        
        print(f"🚀 Experiment started: {exp_id}")
        return exp_id
    
    def log_performance(self, 
                       train_mae: float, train_rmse: float,
                       val_mae: float, val_rmse: float,
                       test_mae: float = None, test_rmse: float = None):
        """성능 지표 기록"""
        self.current_exp["performance"] = {
            "train_mae": train_mae,
            "train_rmse": train_rmse,
            "val_mae": val_mae,
            "val_rmse": val_rmse,
        }
        if test_mae is not None:
            self.current_exp["performance"]["test_mae"] = test_mae
            self.current_exp["performance"]["test_rmse"] = test_rmse
        
        print(f"  Train MAE: {train_mae:.4f} | Val MAE: {val_mae:.4f}")
    
    def log_feature_importance(self, feature_names: list, importances: list, top_k: int = 5):
        """피처 중요도 기록"""
        top_features = sorted(
            zip(feature_names, importances),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        self.current_exp["insights"] = {
            "top_features": [
                {"name": name, "importance": float(imp)}
                for name, imp in top_features
            ]
        }
    
    def log_hyperparameters(self, params: Dict[str, Any]):
        """하이퍼파라미터 기록"""
        self.current_exp["hyperparameters"] = params
    
    def log_note(self, note: str):
        """자유형 메모"""
        if "notes" not in self.current_exp:
            self.current_exp["notes"] = []
        self.current_exp["notes"].append(note)
    
    def save_experiment(self, model_path: str = None):
        """실험 결과 저장"""
        self.current_exp["status"] = "completed"
        if model_path:
            self.current_exp["artifacts"] = {"model_file": model_path}
        
        # JSON 파일로 저장
        save_path = self.metadata_dir / f"{self.current_exp['experiment_id']}.json"
        save_path.write_text(json.dumps(self.current_exp, indent=2, ensure_ascii=False))
        
        print(f"✅ Experiment saved: {save_path}")
        
        # 전체 실험 요약 CSV 생성
        self._update_summary_csv()
    
    def _update_summary_csv(self):
        """모든 실험을 CSV로 요약"""
        experiments = []
        
        for json_file in self.metadata_dir.glob("exp_*.json"):
            data = json.loads(json_file.read_text())
            exp_summary = {
                "Exp ID": data.get("experiment_id"),
                "Model": data.get("model_info", {}).get("type"),
                "Train MAE": data.get("performance", {}).get("train_mae", ""),
                "Val MAE": data.get("performance", {}).get("val_mae", ""),
                "Test MAE": data.get("performance", {}).get("test_mae", ""),
                "Status": data.get("status"),
                "Timestamp": data.get("timestamp"),
                "Notes": data.get("notes", "")[:100] if data.get("notes") else "",
            }
            experiments.append(exp_summary)
        
        df = pd.DataFrame(experiments)
        df = df.sort_values("Exp ID")
        
        summary_path = self.experiments_dir / "results_summary.csv"
        df.to_csv(summary_path, index=False, encoding="utf-8-sig")
        print(f"📊 Summary saved: {summary_path}")

```

### 사용 예시

```python
# scripts/train_model.py에서
from experiment_tracker import ExperimentTracker

tracker = ExperimentTracker("experiments")

# 1. 실험 시작
tracker.start_experiment(
    model_type="LightGBM",
    config_file="configs/exp_lightgbm_v1.yaml",
    description="LightGBM with interaction features"
)

# 2. 모델 학습 (생략)
model = train_lightgbm(X_train, y_train, X_val, y_val)

# 3. 성능 평가
y_pred_train = model.predict(X_train)
y_pred_val = model.predict(X_val)
y_pred_test = model.predict(X_test)

tracker.log_performance(
    train_mae=mae(y_train, y_pred_train),
    train_rmse=rmse(y_train, y_pred_train),
    val_mae=mae(y_val, y_pred_val),
    val_rmse=rmse(y_val, y_pred_val),
    test_mae=mae(y_test, y_pred_test),
    test_rmse=rmse(y_test, y_pred_test),
)

# 4. 피처 중요도 기록
tracker.log_feature_importance(
    feature_names=feature_cols,
    importances=model.feature_importances_
)

# 5. 메모
tracker.log_note("Good performance on validation set. Ready for test evaluation.")

# 6. 저장
model.save_model("experiments/models/exp_003_model.pkl")
tracker.save_experiment("experiments/models/exp_003_model.pkl")
```

---

## 📊 실험 비교 분석

### 모든 실험을 한눈에 보기

```python
import pandas as pd
import json
from pathlib import Path

def load_all_experiments(experiments_dir="experiments"):
    """모든 실험 결과를 DataFrame으로 로드"""
    metadata_dir = Path(experiments_dir) / "metadata"
    
    results = []
    for json_file in sorted(metadata_dir.glob("exp_*.json")):
        data = json.loads(json_file.read_text())
        row = {
            "Exp": data["experiment_id"],
            "Model": data["model_info"]["type"],
            "Train_MAE": data["performance"]["train_mae"],
            "Val_MAE": data["performance"]["val_mae"],
            "Test_MAE": data["performance"].get("test_mae", None),
            "Improvement": None,  # 계산할 예정
        }
        results.append(row)
    
    df = pd.DataFrame(results)
    
    # Baseline (Ridge) 성능 대비 개선도 계산
    baseline_val_mae = df[df["Model"] == "Ridge"].iloc[0]["Val_MAE"]
    df["Improvement"] = (1 - df["Val_MAE"] / baseline_val_mae) * 100
    
    return df.sort_values("Val_MAE")

# 실행
df = load_all_experiments()
print(df)
print("\n🏆 TOP 5 모델:")
print(df.head(5)[["Exp", "Model", "Val_MAE", "Improvement"]])
```

**출력 예시:**
```
       Exp  Model  Train_MAE  Val_MAE  Improvement
exp_002  XGBoost      0.0892   0.0891       0.44%
exp_003  LightGBM    0.0847   0.0912      -2.35%
exp_001  Ridge       0.0950   0.0914       0.00%
exp_004  TabNet      0.0923   0.0925      -1.20%
```

---

## 🎯 실험 추적 체크리스트

### 매 실험마다 체크
- [ ] Experiment ID 자동 생성됨
- [ ] 모델 타입, 설정파일 기록
- [ ] Train/Val/Test MAE, RMSE 기록
- [ ] 피처 중요도 Top 5 기록
- [ ] 하이퍼파라미터 기록
- [ ] 특이사항 메모
- [ ] 모델 파일 저장
- [ ] JSON 메타데이터 저장

### 주 1회 검토
- [ ] `results_summary.csv` 생성 확인
- [ ] Top 5 모델 성능 비교
- [ ] 다음 실험 방향 결정

### 프로젝트 완료 전
- [ ] 모든 실험 메타데이터 검토
- [ ] 최고 성능 모델 재현 가능 여부 확인
- [ ] 모델 성능 개선 트렌드 분석 (그래프)

---

## 💡 팁

### Tip 1: 실험 이름 짓기
```
✅ 좋은 예:
  - exp_003_lightgbm_v1
  - exp_010_tabnet_with_interaction_features
  - exp_015_segment_model_high_load

❌ 나쁜 예:
  - exp_3
  - model_new
  - final_model_v5
```

### Tip 2: 메모는 짧고 구체적으로
```
✅ 좋은 예:
  "Added interaction features (DWATT × TTXM, DWATT × NQJ). 
   Performance improved by 2.1% on validation set."

❌ 나쁜 예:
  "tried some stuff"
  "need to improve"
```

### Tip 3: 모델 저장 전략
```
- experiments/models/exp_*.pkl      : 모든 실험의 모델 (비교용)
- models/production_model_v1.pkl    : 최종 선택 모델 (배포용)
- models/archive/                   : 이전 버전들
```

---

**다음 문서**: `03_Hyperparameter_Tuning.md` (체계적 튜닝 방법)
