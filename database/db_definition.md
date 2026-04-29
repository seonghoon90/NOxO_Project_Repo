# 🗄️ 데이터베이스 및 컬럼 정의서 (v1.0)

본 문서는 IGCC NOx 예측 디지털 트윈 프로젝트의 데이터 엔지니어링 파트 표준 정의서입니다. 모든 팀원은 본 문서에 정의된 컬럼명과 스키마를 기준으로 개발을 진행합니다.

---

## 1. 데이터 컬럼 매핑 정의서
원천 CSV 데이터의 복잡한 태그명을 직관적인 `snake_case`로 매핑한 결과입니다.

| 원본 TagName (CSV) | 변경 후 컬럼명 (DB) | 데이터 타입 | 논리명 (한글) | 역할 |
| :--- | :--- | :--- | :--- | :--- |
| **`TagName`** | **`measured_at`** | TIMESTAMP | 측정 시간 | **Primary Key** |
| `IGCC.DeNOX.AT_H1_901_PV` | **`nox_ppm`** | FLOAT | 가스터빈 후단 NOx 농도 | **Target** |
| `IGCC.CC.G1.NQKR3_MONITOR` | **`dgan_offset`** | INTEGER | 희석질소 오프셋 | **Control** |
| `IGCC.CC.G1.ca_fqsg_cl` | **`syngas_flow`** | FLOAT | 합성가스 유량 | Feature |
| `IGCC.CC.G1.DWATT` | **`generator_output`** | FLOAT | 발전기 출력 | Feature |
| `IGCC.CC.G1.VNPR_P` | **`npr_primary`** | FLOAT | 1차 노즐 압력비 | Feature (안정성) |
| `IGCC.CC.G1.ATID` | **`ambient_temp`** | FLOAT | 대기 온도 | Feature (외기) |
| `IGCC.CC.G1.NQJ` | **`dgan_flow`** | FLOAT | 희석질소 유량 | Feature |
| `IGCC.CC.G1.CSGV` | **`igv`** | FLOAT | IGV 개도 | Feature |

---

## 2. 데이터 적재 및 전처리 규칙

### 2.1. 데이터 정제 (Pre-processing)
* **메타데이터 스킵:** 원본 CSV의 상단 1~4행(Description, Units, Plot Min, Plot Max)은 적재 시 제외합니다.
* **불필요 컬럼 제거:** 유효 데이터가 부족한 `IGCC.CC.G1.ttfr1` 및 전체 결측치인 `Column1`은 적재하지 않습니다.
* **결측치 처리:** `measured_at`이 유효하지 않은 행은 삭제 처리합니다.

### 2.2. 적재 환경 (Storage)
* **DBMS:** PostgreSQL 15 (Docker Container)
* **포트:** 5432
* **데이터베이스명:** `igcc_db`
* **테이블명:** `sensor_data`

---

## 3. DB 스키마 (Entity Relationship)

### 3.1. 핵심 테이블 요약
* **sensor_data:** 가스터빈 센서 측정값 (1초 단위, 약 130만 건)
* **simulation_session_log:** 시뮬레이션 세션 라이프사이클 관리 (`sid` 기준)
* **simulation_input_log:** 세션 내 사용자 제어 입력(▲▼) 이벤트 이력
* **prediction_log:** 미래 시점 NOx 예측 요청 및 결과 기록
* **threshold_config:** NOx 법적 허용치 등 기준값 관리

### 3.2. 데이터 타입 원칙
* 모든 ID 값은 향후 확장성을 고려하여 **BIGINT** 타입을 사용합니다.
* 세션 식별자(`sid`)는 UUID 형식의 **VARCHAR(36)**을 사용합니다.
* 수치 데이터는 소수점 정밀도를 위해 **FLOAT** 타입을 사용합니다.

---

## 4. 비고 (Note)
* 컬럼 추가나 명칭 변경이 필요한 경우 데이터 엔지니어(코치)와 협의 후 본 문서를 업데이트해야 합니다.
* 모든 백엔드 API 응답과 프론트엔드 차트 데이터는 본 문서의 `변경 후 컬럼명`을 따릅니다.
