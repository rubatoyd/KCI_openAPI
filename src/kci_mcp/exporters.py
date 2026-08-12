"""수집 결과(Article)를 xlsx/csv/json/sqlite 로 저장. (scienceon-mcp 패턴 재사용)"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path
from typing import Sequence

from .models import COLUMNS, Article

# 윈도 예약 장치명 — 확장자를 붙여도 파일로 만들 수 없다
_RESERVED = {"CON", "PRN", "AUX", "NUL",
             *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def safe_name(name: str) -> str:
    """출력 파일명으로만 쓰이도록 정규화 — **경로가 되지 않게** 한다.

    ⚠️ `name` 은 MCP 도구 인자이고 미지정 시 검색어가 그대로 들어온다. 즉 **사용자 입력이
       파일 경로에 직접 닿는다.** 정규화 없이 `out_dir / f"{name}.json"` 을 쓰면
       `name="../escaped"` 가 out_dir **밖에** 파일을 쓰고(실측 확인),
       `name="sub/dir/x"` 는 FileNotFoundError 로 조용히 실패한다.
    """
    n = name.replace("\\", "/").split("/")[-1]     # 경로 성분 제거 — 마지막 조각만
    n = n.replace("..", "_")                        # 남은 상위이동 표기
    n = re.sub(r'[<>:"|?*\x00-\x1f]', "_", n)       # 윈도 금지문자·제어문자
    n = n.strip(". ")                               # 후행 점·공백(윈도에서 잘림)
    if n.split(".")[0].upper() in _RESERVED:
        n = f"_{n}"
    return n[:60] or "output"


def _rows(records: Sequence[Article]) -> list[dict]:
    return [r.to_row() for r in records]


def to_json(records: Sequence[Article], path: str) -> None:
    data = [{**r.to_row(), "raw": r.raw} for r in records]
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def to_csv(records: Sequence[Article], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # 엑셀 한글 호환 BOM
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(_rows(records))


def to_xlsx(records: Sequence[Article], path: str) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "records"
    ws.append(COLUMNS)
    for row in _rows(records):
        ws.append([row.get(c, "") for c in COLUMNS])
    wb.save(path)


def to_sqlite(records: Sequence[Article], path: str, *, table: str = "records") -> None:
    con = sqlite3.connect(path)
    try:
        cols = ", ".join(f'"{c}" TEXT' for c in COLUMNS)
        con.execute(f"DROP TABLE IF EXISTS {table}")  # 스냅샷: 재실행 시 누적 방지
        con.execute(f'CREATE TABLE {table} ({cols}, "raw" TEXT)')
        ph = ", ".join(["?"] * (len(COLUMNS) + 1))
        for r in records:
            row = r.to_row()
            con.execute(
                f'INSERT INTO {table} ({", ".join(COLUMNS)}, raw) VALUES ({ph})',
                [row.get(c, "") for c in COLUMNS] + [json.dumps(r.raw, ensure_ascii=False)],
            )
        con.commit()
    finally:
        con.close()


_EXPORTERS = {"json": to_json, "csv": to_csv, "xlsx": to_xlsx, "sqlite": to_sqlite}
_EXT = {"json": ".json", "csv": ".csv", "xlsx": ".xlsx", "sqlite": ".sqlite"}


def export(records: Sequence[Article], formats: Sequence[str], out_dir: str, name: str) -> list[str]:
    """formats 각각으로 out_dir/name.* 저장. 저장된 경로 목록 반환."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    name = safe_name(name)
    paths: list[str] = []
    for fmt in formats:
        if fmt not in _EXPORTERS:
            raise ValueError(f"지원하지 않는 출력형식: {fmt} (가능: {list(_EXPORTERS)})")
        p = out / f"{name}{_EXT[fmt]}"
        # 이중 확인 — 정규화를 우회하는 입력이 나오더라도 out_dir 밖에는 절대 쓰지 않는다
        if out.resolve() not in p.resolve().parents:
            raise ValueError(f"출력 경로가 out_dir 를 벗어납니다: {name!r}")
        _EXPORTERS[fmt](records, str(p))
        paths.append(str(p))
    return paths
