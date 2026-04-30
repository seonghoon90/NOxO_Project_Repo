# NOxO Project - Claude 작업 지침

## 커밋 & 푸시 규칙

### 커밋/푸시 요청 시 반드시 아래 순서를 따른다

1. **브랜치 확인** (`git branch`)
   - 작업 내용과 현재 브랜치가 일치하는지 확인
   - 이상이 있으면 사용자에게 먼저 알린다

2. **작업 폴더만 add** (`git add <작업중인_폴더/파일>`)
   - `git add .` 또는 `git add -A` 금지
   - 현재 작업 중인 폴더/파일만 명시적으로 스테이징

3. **커밋 메시지 작성 후 커밋**
   - 아래 커밋 규칙에 맞춰 메시지 작성
   - `git commit -m "이모지 타입 : 설명"`

4. **최종 확인 후 푸시**
   - `git status`, `git log -1` 로 이상 없는지 확인
   - 확인 후 `git push`

---

## 커밋 메시지 형식

```
이모지 타입 : 작업 내용
```

**예시:**
```
✨ feat : 게시글 등록 기능
🐛 bugfix : 로그인 토큰 만료 오류 수정
```

---

## 작업 타입 목록

| 이모지 | 타입 | 설명 |
|--------|------|------|
| ✨ | feat | 새로운 기능 추가 |
| 🎉 | add | 파일 생성, 초기 세팅 |
| 🐛 | bugfix | 버그 수정 |
| ♻️ | refactor | 코드 리팩토링 |
| 🩹 | fix | 코드 수정 |
| 🚚 | move | 파일 이동/정리 |
| 🔥 | del | 기능/파일 삭제 |
| 🍻 | test | 테스트 코드 작성 |
| 💄 | style | CSS 스타일 작업 |
| 🙈 | gitfix | .gitignore 수정 |
| 🔨 | script | package.json 변경 (npm 설치 등) |

---

## 폴더 구조 & 브랜치 매핑

```
NOxO_Project_Repo/
├── apps/
│   ├── frontend/    # 프론트엔드
│   └── backend/     # 백엔드
├── analysis/        # 데이터 분석 (notebooks, reports)
├── data/            # 데이터셋
├── database/        # DB 관련
├── digital_twin/    # 디지털 트윈
└── docs/            # 문서
```

- **main** : 배포용 (직접 커밋 지양)
- **dev** : 개발 통합 브랜치

---

## Issues 제목 형식

```
[TASK] XXX 기능 구현
```
