#!/usr/bin/env python3
"""GitHub 현황 수집: 커밋·푸시 활동, Pages 상태, 저장소 용량, Actions 누적 실행시간.
표준 라이브러리만 사용. 환경변수 GH_PAT(필수), GH_OWNER(기본: 토큰 소유자)."""
import json, os, sys, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

API = "https://api.github.com"
TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "docs" / "data.json"
NOW = datetime.now(timezone.utc)
iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
parse = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def get(path, params=""):
    req = urllib.request.Request(f"{API}{path}{params}", headers={
        "Authorization": f"Bearer {TOKEN}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "gh-monitor"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code in (404, 409):  # Pages 미설정, 빈 저장소 등
            return None
        raise


def paged(path, key=None, params=""):
    page, items = 1, []
    while page <= 10:
        d = get(path, f"{params}{'&' if params else '?'}per_page=100&page={page}")
        if not d:
            break
        chunk = d[key] if key else d
        items += chunk
        if len(chunk) < 100:
            break
        page += 1
    return items


def main():
    if not TOKEN:
        sys.exit("GH_PAT 환경변수가 필요합니다")
    prev = json.loads(OUT.read_text()) if OUT.exists() else {"repos": {}}
    repos = [r for r in paged("/user/repos", params="?affiliation=owner&sort=pushed")
             if not r["archived"]]
    out = {"updated": iso(NOW), "repos": {}}
    since7, since30 = iso(NOW - timedelta(days=7)), iso(NOW - timedelta(days=30))

    for r in repos:
        name, full = r["name"], r["full_name"]
        old = prev["repos"].get(name, {})
        # 커밋 활동 (기본 브랜치, 최근 30일)
        commits = paged(f"/repos/{full}/commits", params=f"?since={since30}") or []
        c30 = len(commits)
        c7 = sum(1 for c in commits if c["commit"]["author"]["date"] >= since7)
        last = commits[0]["commit"] if commits else None
        # Pages 상태
        pg = get(f"/repos/{full}/pages")
        pages = None
        if pg:
            b = get(f"/repos/{full}/pages/builds/latest") or {}
            pages = {"url": pg.get("html_url"), "status": pg.get("status"),
                     "build": b.get("status"), "build_at": b.get("updated_at"),
                     "error": (b.get("error") or {}).get("message")}
        # Actions 누적 실행시간: 마지막 확인 이후 완료된 run 만 추가 (분 단위, 반올림 없이 초 누적)
        seen = old.get("actions_checked") or iso(NOW - timedelta(days=30))
        runs = paged(f"/repos/{full}/actions/runs", key="workflow_runs",
                     params=f"?created=>{seen}&status=completed")
        add_s, fails = 0, 0
        for run in runs:
            if run.get("run_started_at") and run.get("updated_at"):
                add_s += max(0, int((parse(run["updated_at"]) - parse(run["run_started_at"])).total_seconds()))
            fails += run.get("conclusion") == "failure"
        out["repos"][name] = {
            "full_name": full, "private": r["private"], "url": r["html_url"],
            "size_kb": r["size"], "pushed_at": r["pushed_at"],
            "commits_7d": c7, "commits_30d": c30,
            "last_commit": {"msg": last["message"].splitlines()[0][:80], "at": last["author"]["date"]} if last else None,
            "pages": pages,
            "actions_total_sec": old.get("actions_total_sec", 0) + add_s,
            "actions_runs_total": old.get("actions_runs_total", 0) + len(runs),
            "actions_fail_total": old.get("actions_fail_total", 0) + fails,
            "actions_checked": iso(NOW),
        }
        print(f"{name}: c7={c7} c30={c30} size={r['size']}KB runs+={len(runs)}")

    # 일별 히스토리 (용량·누적시간 추이)
    hist = prev.get("history", [])
    today = NOW.strftime("%Y-%m-%d")
    snap = {"date": today,
            "size_kb": sum(v["size_kb"] for v in out["repos"].values()),
            "actions_min": round(sum(v["actions_total_sec"] for v in out["repos"].values()) / 60, 1)}
    hist = [h for h in hist if h["date"] != today] + [snap]
    out["history"] = hist[-365:]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
