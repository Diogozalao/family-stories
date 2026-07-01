"""Ad-hoc backup of all domain data to a timestamped JSON file.

Supabase's free tier has **no restorable backups**, so this script dumps every
domain table to disk. Run it periodically — manually or from cron:

    venv/bin/python -m backend.scripts.backup_data

The JSON keeps every column of every row, so the data survives even if the
tables are accidentally dropped. Restore is a manual re-insert from the file
(the auth accounts and the Storage files are managed separately by Supabase and
are not part of this dump).
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import uuid
from pathlib import Path

from sqlalchemy import text

from backend.core.database import AsyncSessionLocal

# Domain tables, in a dependency-friendly order (parents before children).
TABLES = [
    "projects",
    "persons",
    "relationships",
    "media_files",
    "project_media",
    "timeline_events",
    "stories",
    "video_outputs",
    "task_records",
]


def _serialize(value):
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


async def main() -> None:
    dump: dict = {
        "exported_at": dt.datetime.now(dt.UTC).isoformat(),
        "tables": {},
    }
    async with AsyncSessionLocal() as db:
        for table in TABLES:
            try:
                rows = (await db.execute(text(f"SELECT * FROM {table}"))).mappings().all()
                dump["tables"][table] = [
                    {k: _serialize(v) for k, v in dict(row).items()} for row in rows
                ]
                print(f"  {table:16} {len(rows):>5} linhas")
            except Exception as exc:                       # keep going on any table
                print(f"  {table:16} ERRO: {exc}")
                dump["tables"][table] = {"error": str(exc)}

    folder = Path("backups")
    folder.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = folder / f"backup_{stamp}.json"
    path.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")

    total = sum(len(v) for v in dump["tables"].values() if isinstance(v, list))
    print(f"\n✅ Backup guardado em {path}  ({total} linhas no total)")


if __name__ == "__main__":
    asyncio.run(main())
