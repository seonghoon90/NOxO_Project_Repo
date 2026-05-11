import sys
from pathlib import Path

# digital_twin 디렉토리 자체 + 프로젝트 루트 모두 path에 추가.
# - digital_twin/ : 기존 `from simulation import ...` 등 단독 import 유지
# - 프로젝트 루트 : `from digital_twin.preprocess import ...` (B6 정정) 지원
_THIS = Path(__file__).resolve()
_DT_DIR = _THIS.parent.parent
_PROJECT_ROOT = _DT_DIR.parent
sys.path.insert(0, str(_DT_DIR))
sys.path.insert(0, str(_PROJECT_ROOT))
