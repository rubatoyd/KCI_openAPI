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


README = Path(os.environ.get("USAGE_README", "README.md"))
CHART = Path(os.environ.get("USAGE_SVG", "docs/usage.svg"))
MARK_A, MARK_B = "<!-- usage:start -->", "<!-- usage:end -->"

# GitHub 은 README 의 라이트/다크 테마를 오가므로 **양쪽에서 읽히는 색**만 쓴다.
# (SVG 안의 <style> media query 는 GitHub 이미지 렌더링에서 신뢰할 수 없다.)
_CLONE, _VIEW, _AXIS = "#3b82f6", "#f59e0b", "#8b949e"


def write_chart(rows: dict[str, dict]) -> bool:
    """일별 클론·조회 추이를 **의존성 없이** SVG 로 그린다.

    matplotlib 같은 것을 끌어오면 워크플로가 무거워지고 실패 지점이 는다.
    선 두 개짜리 그래프에 그럴 이유가 없어 좌표를 직접 찍는다.
    """
    dates = sorted(rows)
    if len(dates) < 2:
        return False
    clones = [int(rows[d].get("clones") or 0) for d in dates]
    views = [int(rows[d].get("views") or 0) for d in dates]
    hi = max(max(clones), max(views), 1)

    W, H, PAD_L, PAD_B, PAD_T = 720, 200, 34, 26, 16
    iw, ih = W - PAD_L - 10, H - PAD_B - PAD_T

    def pts(vals):
        n = len(vals) - 1 or 1
        return " ".join(f"{PAD_L + i * iw / n:.1f},{PAD_T + ih - v * ih / hi:.1f}"
                        for i, v in enumerate(vals))

    # y 눈금 3개 · x 라벨은 처음/중간/끝만(겹침 방지)
    ticks = "".join(
        f'<line x1="{PAD_L}" y1="{PAD_T + ih - f * ih:.1f}" x2="{W - 10}" '
        f'y2="{PAD_T + ih - f * ih:.1f}" stroke="{_AXIS}" stroke-opacity=".25"/>'
        f'<text x="{PAD_L - 6}" y="{PAD_T + ih - f * ih + 4:.1f}" font-size="10" '
        f'fill="{_AXIS}" text-anchor="end">{int(hi * f)}</text>'
        for f in (0, 0.5, 1))
    xl = "".join(
        f'<text x="{PAD_L + i * iw / (len(dates) - 1):.1f}" y="{H - 8}" font-size="10" '
        f'fill="{_AXIS}" text-anchor="{a}">{dates[i][5:]}</text>'
        for i, a in ((0, "start"), (len(dates) // 2, "middle"), (len(dates) - 1, "end")))

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" \
viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,sans-serif" role="img" \
aria-label="일별 클론·조회 추이">
<title>일별 클론·조회 추이 ({dates[0]} ~ {dates[-1]})</title>
{ticks}{xl}
<polyline fill="none" stroke="{_CLONE}" stroke-width="2" points="{pts(clones)}"/>
<polyline fill="none" stroke="{_VIEW}" stroke-width="2" points="{pts(views)}"/>
<circle cx="{W - 150}" cy="12" r="4" fill="{_CLONE}"/>
<text x="{W - 140}" y="16" font-size="11" fill="{_AXIS}">clones</text>
<circle cx="{W - 78}" cy="12" r="4" fill="{_VIEW}"/>
<text x="{W - 68}" y="16" font-size="11" fill="{_AXIS}">views</text>
</svg>
"""
    CHART.parent.mkdir(parents=True, exist_ok=True)
    CHART.write_text(svg, encoding="utf-8")
    return True


def update_readme(rows: dict[str, dict], snap: dict, today: str) -> None:
    """README 의 표시 블록을 갱신한다 (마커가 있을 때만).

    조회·클론은 **최근 14일 합**이다 — GitHub 가 그 창만 주므로 '누적'이라 쓰면 거짓이 된다.
    다운로드는 릴리스 자산 누적이라 성격이 다르니 따로 표기한다.
    """
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    if MARK_A not in text or MARK_B not in text:
        print(f"  (README 에 {MARK_A} 마커가 없어 건너뜀)")
        return

    recent = sorted(rows)[-14:]
    def s(key: str) -> int:
        return sum(int(rows[d].get(key) or 0) for d in recent)

    dl = snap.get("release_downloads") or "—"
    chart = f"\n>\n> ![일별 클론·조회 추이]({CHART.as_posix()})\n" if write_chart(rows) else ""
    body = (f"> 📈 **사용량** — 최근 14일 조회 **{s('views'):,}**회(고유 {s('view_uniques'):,}) · "
            f"클론 **{s('clones'):,}**회(고유 {s('clone_uniques'):,}) · "
            f"릴리스 자산 누적 다운로드 **{dl}**"
            f"{chart}"
            f">\n> <sub>{today} 자동 갱신 · 전체 이력은 [`docs/usage.csv`](docs/usage.csv). "
            f"GitHub 트래픽 통계는 14일 창만 제공하므로 이 저장소가 매일 찍어 누적한다.</sub>")

    head, rest = text.split(MARK_A, 1)
    _old, tail = rest.split(MARK_B, 1)
    README.write_text(f"{head}{MARK_A}\n{body}\n{MARK_B}{tail}", encoding="utf-8")
    print(f"  README 사용량 블록 갱신")


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

    # ⚠️ 성공했으면 **비워야 한다.** `if notes:` 로만 쓰면 예전 실패가 남긴 '권한없음' 이
    #    토큰을 넣은 뒤에도 영영 남아 "아직 권한이 없다"는 거짓 신호가 된다(실측으로 확인).
    snap["note"] = ";".join(notes)

    # ── 저장 (날짜 오름차순) ──────────────────────────────────────────────────
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for d in sorted(rows):
            w.writerow({k: rows[d].get(k, "") for k in FIELDS})

    update_readme(rows, snap, today)

    print(f"{REPO}: {before} → {len(rows)}행  ({OUT})")
    print(f"  오늘({today}) 스냅샷: 다운로드 {snap['release_downloads']} · "
          f"스타 {snap['stars']} · 조회 {snap['views']} · 클론 {snap['clones']}")
    if notes:
        print(f"  ⚠️ 결손: {';'.join(notes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
