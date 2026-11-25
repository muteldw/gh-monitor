# gh-monitor

GitHub 저장소 현황(커밋·푸시, Pages 배포, 용량, Actions 누적 실행시간)을 6시간마다 수집해 Pages 대시보드로 보여줍니다.

## 설정 (1회)
1. Settings → Secrets and variables → Actions → `GH_PAT` 등록
   (Fine-grained 또는 classic PAT, 권한: 모든 저장소 Contents·Metadata·Actions·Pages **Read**; classic은 `repo` 스코프)
2. Settings → Pages → Branch `main` / `/docs`
3. Actions 탭 → "GitHub 현황 수집" → Run workflow

## 참고
- Actions 누적 시간은 run 시작~종료 시간 합계(실제 과금 분과 다를 수 있음). 수집 시작 시점부터 누적됩니다.
- 용량은 GitHub가 보고하는 저장소 크기(KB)입니다.
