# Git 작업 컨벤션

## 최초 1회 환경 설정

특별한 환경 설정은 필요하지 않다.

> **2026-05 변경**: 이전 버전의 `.githooks/pre-commit` + `scripts/sync-agents-md.sh` 기반 `CLAUDE.md ↔ AGENTS.md` 양방향 sync 자동화는 폐기되었다.
> 이제 본문은 `AGENTS.md`에만 작성하고, `CLAUDE.md`는 `@./AGENTS.md` 한 줄로 import 한다. Claude Code는 import를 자동으로 따라가며 Codex/Antigravity/Cursor는 `AGENTS.md`를 직접 읽으므로, 단일 파일만 편집하면 된다(sync drift가 구조적으로 불가능).
> 따라서 기존에 적용했던 `git config core.hooksPath .githooks` 설정이 있다면 다음으로 해제할 수 있다:
>
> ```bash
> git config --unset core.hooksPath
> ```

## 작업 시작 시 (필수)

새 작업 시작 전 항상 dev 브랜치 동기화 상태를 확인한다.

```bash
git fetch origin
git log HEAD..origin/dev --oneline
```

- 출력이 비어있으면 그대로 진행
- 새 커밋이 있으면 현재 브랜치에 merge:
  ```bash
  git merge origin/dev
  ```

이유: dev에 누적된 변경사항을 미리 가져와 push 시점의 conflict를 방지.

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

4. **push 직전 dev 동기화 재확인**
   ```bash
   git fetch origin
   git log HEAD..origin/dev --oneline
   ```
   - 새 커밋이 있으면 merge 후 push (작업 도중 dev에 변경이 있을 수 있음)

5. **최종 확인 후 푸시**
   - `git status`, `git log -1` 로 이상 없는지 확인
   - `git push`

## 커밋 메시지 형식

이모지 타입 : 작업 내용

**예시:**
✨ feat : 게시글 등록 기능
🐛 bugfix : 로그인 토큰 만료 오류 수정

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
| 📝 | docs | 문서 작업 |
| 🔗 | link | 심볼릭 링크 등 연결 작업 |

## 브랜치 매핑

- **main** : 배포용 (직접 커밋 지양)
- **dev** : 개발 통합 브랜치
- **feature 브랜치** : `<type>/<description>` (예: `feat/dashboard-trend-plot`, `docs/claude-md-map`)

## ⚠️ LEARNED CAUTIONS

- (2026-05-14) 명시 승인 없이 `git push`를 임의 실행하지 말 것. 커밋까지만 진행하고 push는 사용자 확정 후에만.
