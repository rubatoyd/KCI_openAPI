"""저장소 사용량을 `docs/usage.csv` 에 **누적 기록**한다 (GitHub Actions 일일 실행용).

왜 필요한가 — GitHub 의 트래픽(조회·클론) 통계는 **14일 롤링 윈도**라 그 뒤로는 사라진다.
릴리스 자산 다운로드 수만 영구 누적된다. 장기 추세를 보려면 주기적으로 찍어 두는 수밖에 없다.

핵심 설계: **날짜 키로 병합(upsert)한다.** 오늘 값을 덧붙이는 게 아니라 API 가 주는
14일치 일별 값을 통째로 받아 기존 행을 갱신한다. 그래서
  · 워크플로가 며칠 쉬어도 **최대 13일까지 자동으로 메워진다**
  · 당일 수치가 나중에 올라가도(집계 지연) 다음 실행이 바로잡는다
단순 append 로 짰다면 중복 행이 쌓이고 결손은 영영 못 메운다.

⚠️ 트래픽 API 는 **push 권한**을 요구한다. **Actions 의 기본 `GITHUB_TOKEN` 으로는 403 이다**
   (2026-08-12 실측 확인). 조회·클론까지 남기려면 저장소 Secrets 에 `USAGE_TOKEN` 을 넣어야 한다
   — classic PAT(scope: `repo`) 또는 fine-grained PAT(권한: Administration → Read).
   토큰이 없어도 실패로 끝내지 않고 다운로드·스타 스냅샷만 기록하고 `note` 에 사유를 남긴다
   (부분 기록이 무기록보다 낫다).
"""
from __future__ import annotations

import csv
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = os.environ.get("GITHUB_REPOSITORY", "")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = Path(os.environ.get("USAGE_CSV", "docs/usage.csv"))

# 트래픽(일별) + 스냅샷(그날 시점의 누적값)
FIELDS = ["date", "views", "view_uniques", "clones", "clone_uniques",
          "release_downloads", "releases", "stars", "forks", "note"]


def api(path: str = ""):
    """GitHub API GET. 403/404 는 None 을 돌려주고 호출부가 사유를 기록한다.

    ⚠️ 빈 path 로 후행 슬래시를 붙이면 404 다(`repos/owner/name/` ≠ `repos/owner/name`).
       로컬 리허설에서 저장소 메타(스타·포크)가 통째로 빠지는 것으로 드러났다.
    """
    url = f"https://api.github.com/repos/{REPO}" + (f"/{path}" if path else "")
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {TOKEN}",
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "usage-recorder"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  !! {path} → HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:  # noqa: BLE001
        print(f"  !! {path} → {type(e).__name__}", file=sys.stderr)
        return None


def load() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    with OUT.open(encoding="utf-8") as f:
        return {row["date"]: row for row in csv.DictReader(f)}


def main() -> int:
    if not REPO or not TOKEN:
        print("GITHUB_REPOSITORY / GITHUB_TOKEN 이 필요합니다.", file=sys.stderr)
        return 1

    rows = load()
    before = len(rows)
    notes: list[str] = []

    def touch(d: str) -> dict:
        return rows.setdefault(d, {**{k: "" for k in FIELDS}, "date": d})

    # ── 트래픽 14일치 일별 병합 ────────────────────────────────────────────────
    for kind, keys in (("views", ("views", "view_uniques")),
                       ("clones", ("clones", "clone_uniques"))):
        data = api(f"traffic/{kind}")
        if data is None:
            notes.append(f"{kind}:권한없음")
            continue
        for item in data.get(kind, []):
            d = item["timestamp"][:10]
            r = touch(d)
            r[keys[0]] = item["count"]
            r[keys[1]] = item["uniques"]

    # ── 오늘 시점 스냅샷(누적값) ──────────────────────────────────────────────
    today = datetime.now(timezone.utc).date().isoformat()
    snap = touch(today)

    rel = api("releases")
    if rel is not None:
        snap["release_downloads"] = sum(a.get("download_count", 0)
                                        for x in rel for a in x.get("assets", []))
        snap["releases"] = len(rel)
    else:
        notes.append("releases:조회실패")

    meta = api("")
    if meta is not None:
        snap["stars"] = meta.get("stargazers_count", "")
        snap["forks"] = meta.get("forks_count", "")
    else:
        notes.append("repo:조회실패")

    if notes:
        snap["note"] = ";".join(notes)

    # ── 저장 (날짜 오름차순) ──────────────────────────────────────────────────
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for d in sorted(rows):
            w.writerow({k: rows[d].get(k, "") for k in FIELDS})

    print(f"{REPO}: {before} → {len(rows)}행  ({OUT})")
    print(f"  오늘({today}) 스냅샷: 다운로드 {snap['release_downloads']} · "
          f"스타 {snap['stars']} · 조회 {snap['views']} · 클론 {snap['clones']}")
    if notes:
        print(f"  ⚠️ 결손: {';'.join(notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
