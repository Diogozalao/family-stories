"""Seed a demo Supabase account pre-populated with photos + a family tree.

Run once whenever you want a fresh, populated showcase user. Idempotent:
re-running with the same email upserts where it can and does not duplicate
rows.

Usage::

    venv/bin/python -m backend.scripts.seed_demo

Defaults:
    Email:    diogo.lopes.dinis@ubi.pt
    Password: memoria_viva13      (override with --password)
    Display:  Diogo

Side effects:
  1. Creates (or reuses) the user via the Supabase Admin API.
  2. Generates 6 placeholder JPGs with PIL and uploads them to the
     ``photos`` Storage bucket under ``{user_id}/photos/``.
  3. Inserts the matching ``media_files`` rows.
  4. Inserts a 9-person ``Dinis`` family with parent/child relations on
     a serialised NetworkX graph at
     ``data/processed/graphs/{user_id}.json``.
  5. Inserts a hand-written sample story.

If anything fails midway, the script logs the failure and exits non-zero
so you can re-run after fixing the environment (e.g. Supabase pooler
back online).
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import asyncpg
import httpx
from PIL import Image, ImageDraw

# Ensure the project root is on sys.path so ``backend.*`` imports work
# when invoking the file directly.
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv     # noqa: E402
load_dotenv(ROOT / ".env")

from backend.core.config import settings   # noqa: E402

# ── Defaults ──────────────────────────────────────────────────
DEFAULT_EMAIL    = "diogo.lopes.dinis@ubi.pt"
DEFAULT_NAME     = "Diogo"
DEFAULT_PASSWORD = "memoria_viva13"
FAMILY_LABEL     = "Dinis"

# Synthetic family tree — three generations of the Dinis line.
DINIS_FAMILY = [
    # (gedcom_id, name, birth_year, birth_place, role_in_tree)
    ("I1",  "António Dinis",          1925, "Belmonte, Castelo Branco",  "grandfather"),
    ("I2",  "Maria Pinheiro",         1928, "Covilhã, Castelo Branco",   "grandmother"),
    ("I3",  "Carlos Dinis",           1955, "Covilhã, Castelo Branco",   "father"),
    ("I4",  "Eulália Sousa",          1958, "Évora, Portugal",            "mother"),
    ("I5",  "Joaquim Dinis",          1960, "Covilhã, Castelo Branco",   "uncle"),
    ("I6",  "Beatriz Carmo",          1962, "Vila Viçosa, Évora",         "aunt"),
    ("I7",  "Diogo Dinis",            2002, "Covilhã, Castelo Branco",   "self"),
    ("I8",  "Filipe Dinis",           1998, "Covilhã, Castelo Branco",   "brother"),
    ("I9",  "Carolina Dinis",         2005, "Covilhã, Castelo Branco",   "sister"),
]

# Parent → child edges so the FamilyGraph reflects a real lineage.
DINIS_EDGES = [
    ("I1", "I3"), ("I2", "I3"),      # António + Maria → Carlos
    ("I1", "I5"), ("I2", "I5"),      # António + Maria → Joaquim
    ("I3", "I7"), ("I4", "I7"),      # Carlos + Eulália → Diogo
    ("I3", "I8"), ("I4", "I8"),      # Carlos + Eulália → Filipe
    ("I3", "I9"), ("I4", "I9"),      # Carlos + Eulália → Carolina
    ("I5", None),                    # Joaquim married Beatriz (spouse only)
    ("I1", None), ("I3", None),
]
SPOUSE_PAIRS = [("I1", "I2"), ("I3", "I4"), ("I5", "I6")]

# 6 placeholder JPGs — solid-colour squares with a label baked in.
PHOTO_BLUEPRINTS = [
    ("verão_serra_estrela.jpg",   (180,  90,  60), "Serão na Serra · 1972"),
    ("natal_avos.jpg",            (130,  60,  70), "Natal em casa dos avós · 1978"),
    ("casamento_pais.jpg",        ( 90, 110, 140), "Casamento dos pais · 1984"),
    ("baptizado_diogo.jpg",       (110, 150, 100), "Baptizado · 2002"),
    ("praia_algarve.jpg",         (220, 180,  90), "Praia no Algarve · 2008"),
    ("ano_novo_familia.jpg",      ( 70,  90, 120), "Ano novo em família · 2020"),
]


# ── Connection helpers ────────────────────────────────────────

def _admin_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        "apikey":        settings.SUPABASE_SERVICE_ROLE_KEY,
        "Content-Type":  "application/json",
    }


def _db_dsn() -> str:
    """asyncpg DSN derived from SUPABASE_DB_URL (sync ``postgresql://``)."""
    url = settings.SUPABASE_DB_URL
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url[len("postgresql+asyncpg://"):]
    return url


async def _conn() -> asyncpg.Connection:
    """Open a single asyncpg connection sized for one-off scripting."""
    dsn = _db_dsn()
    port = urlparse(dsn).port
    kw: dict = {}
    if port == 6543:
        # Same workaround as backend/core/database.py for the transaction pooler.
        kw["statement_cache_size"] = 0
    return await asyncpg.connect(dsn, timeout=15, **kw)


# ── Supabase Admin API ────────────────────────────────────────

async def find_or_create_user(client: httpx.AsyncClient, email: str, password: str, name: str) -> UUID:
    """Return the Supabase ``auth.users.id`` UUID for ``email``, creating it if missing."""
    base = settings.SUPABASE_URL.rstrip("/")

    # Search first — the admin endpoint lacks a "get by email" filter so
    # we list (paginated) and match. For seed runs this is cheap.
    listed = await client.get(
        f"{base}/auth/v1/admin/users?per_page=200",
        headers=_admin_headers(),
    )
    listed.raise_for_status()
    for u in listed.json().get("users", []):
        if (u.get("email") or "").lower() == email.lower():
            print(f"  · user already exists ({u['id']})")
            return UUID(u["id"])

    # Create.
    payload = {
        "email":         email,
        "password":      password,
        "email_confirm": True,                    # Skip the confirmation email — demo accounts go live immediately.
        "user_metadata": {"username": name},
    }
    r = await client.post(f"{base}/auth/v1/admin/users", headers=_admin_headers(), json=payload)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"create_user failed [{r.status_code}]: {r.text[:300]}")
    uid = UUID(r.json()["id"])
    print(f"  · user created ({uid})")
    return uid


# ── Storage uploads ───────────────────────────────────────────

def make_placeholder_jpg(color: tuple[int, int, int], caption: str, size: int = 1080) -> bytes:
    """Render a square JPG with a centred caption — stand-in for a real photo."""
    img = Image.new("RGB", (size, size), color)
    draw = ImageDraw.Draw(img)
    # No bundled font path is portable — fall back to PIL's default.
    bbox = draw.textbbox((0, 0), caption)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) / 2, (size - h) / 2), caption, fill="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


async def upload_photos(client: httpx.AsyncClient, user_id: UUID) -> list[dict]:
    """Upload the 6 placeholder photos and return one row-payload per upload."""
    bucket = "photos"
    base = settings.SUPABASE_URL.rstrip("/")
    rows: list[dict] = []
    for filename, color, caption in PHOTO_BLUEPRINTS:
        body = make_placeholder_jpg(color, caption)
        key  = f"{user_id}/photos/{filename}"
        url  = f"{base}/storage/v1/object/{bucket}/{key}"
        r = await client.post(
            url,
            headers={**_admin_headers(), "Content-Type": "image/jpeg", "x-upsert": "true"},
            content=body,
        )
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload {filename} failed [{r.status_code}]: {r.text[:200]}")
        rows.append({
            "filename":  filename,
            "key":       key,
            "size":      len(body),
            "caption":   caption,
        })
        print(f"  · uploaded {filename} ({len(body)//1024} KiB)")
    return rows


# ── DB seeding ────────────────────────────────────────────────

async def seed_media(conn: asyncpg.Connection, user_id: UUID, photos: list[dict]) -> list[int]:
    """Insert ``media_files`` rows for each uploaded photo. Returns the new ids."""
    ids: list[int] = []
    for p in photos:
        row = await conn.fetchrow(
            """
            INSERT INTO media_files
                (user_id, original_filename, stored_filename, file_path, file_size,
                 mime_type, media_type, ai_description, ai_setting, status, created_at)
            VALUES
                ($1, $2, $3, $4, $5, 'image/jpeg', 'photo', $6, $7, 'completed', NOW())
            ON CONFLICT (user_id, stored_filename) DO UPDATE
                SET ai_description = EXCLUDED.ai_description
            RETURNING id
            """,
            user_id, p["filename"], p["filename"], p["key"], p["size"],
            p["caption"], p["caption"].split(" · ")[0],
        )
        ids.append(row["id"])
    print(f"  · seeded {len(ids)} media rows")
    return ids


async def seed_family(conn: asyncpg.Connection, user_id: UUID) -> dict[str, int]:
    """Insert the synthetic Dinis tree and return ``{gedcom_id: row_id}``."""
    mapping: dict[str, int] = {}
    for gid, name, byear, place, _role in DINIS_FAMILY:
        row = await conn.fetchrow(
            """
            INSERT INTO persons
                (user_id, name, birth_date, birth_place, gedcom_id, family_label, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, NOW())
            ON CONFLICT (user_id, gedcom_id) DO UPDATE
                SET name         = EXCLUDED.name,
                    birth_place  = EXCLUDED.birth_place,
                    family_label = EXCLUDED.family_label
            RETURNING id
            """,
            user_id, name, datetime(byear, 6, 15, tzinfo=UTC), place, gid, FAMILY_LABEL,
        )
        mapping[gid] = row["id"]
    print(f"  · seeded {len(mapping)} persons in family '{FAMILY_LABEL}'")

    # Persist a per-user NetworkX graph so the M2/M3 modules find it.
    persist_family_graph(user_id, mapping)
    return mapping


def persist_family_graph(user_id: UUID, mapping: dict[str, int]) -> None:
    """Build and serialise a ``data/processed/graphs/{user_id}.json`` graph.

    We write it directly (rather than via NetworkX) so the script has no
    dependency on having M2 importable from this context.
    """
    nodes: list[dict] = []
    for gid, name, byear, place, _role in DINIS_FAMILY:
        nodes.append({
            "id":          mapping[gid],
            "name":        name,
            "birth_date":  f"{byear}-06-15 00:00:00+00:00",
            "birth_place": place,
            "gedcom_id":   gid,
        })

    edges: list[dict] = []
    # Spouses
    for a, b in SPOUSE_PAIRS:
        edges.append({"source": mapping[a], "target": mapping[b], "relation": "cônjuge"})
        edges.append({"source": mapping[b], "target": mapping[a], "relation": "cônjuge"})
    # Parent / child
    for parent_gid, child_gid in DINIS_EDGES:
        if child_gid is None:
            continue
        edges.append({"source": mapping[parent_gid], "target": mapping[child_gid], "relation": "pai/mãe"})
        edges.append({"source": mapping[child_gid], "target": mapping[parent_gid], "relation": "filho de"})

    doc = {"directed": True, "multigraph": False, "graph": {}, "nodes": nodes, "links": edges}
    graph_dir = ROOT / "data" / "processed" / "graphs"
    graph_dir.mkdir(parents=True, exist_ok=True)
    (graph_dir / f"{user_id}.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2))
    print(f"  · wrote family graph for {user_id}")


async def seed_story(conn: asyncpg.Connection, user_id: UUID, media_ids: list[int]) -> None:
    """Drop a single sample story so the dashboard isn't bare."""
    narrative = (
        "A casa dos avós, na Covilhã, tinha sempre o cheiro a pão acabado de "
        "cozer. Foi lá que vi pela primeira vez o álbum dos pais — folhas de "
        "papel cinzento com fotografias coladas em molduras de cartão. O "
        "Verão de 1972, na Serra da Estrela, abre o álbum: a minha avó com a "
        "cabeça encostada ao meu avô e um sol baixo que pinta tudo de cobre.\n\n"
        "Os Natais que se seguem repetem-se com pequenas variações — mais um "
        "primo, mais um sobrinho — e cada um traz uma memória nova para a casa "
        "antiga. Em 2002, o álbum recebeu o meu baptizado: uma fotografia "
        "ligeiramente desenfocada, mas com toda a gente lá."
    )
    await conn.execute(
        """
        INSERT INTO stories
            (user_id, title, event_type, narrative, template_used, llm_backend,
             facts_used, person_ids, status, created_at)
        VALUES
            ($1, $2, 'memoir', $3, 'memoir', 'demo-seed', $4,
             $5::jsonb, 'completed', NOW())
        ON CONFLICT DO NOTHING
        """,
        user_id, "A casa da Covilhã", narrative, len(media_ids),
        json.dumps(media_ids[:3]),
    )
    print("  · seeded sample story")


# ── Orchestrator ──────────────────────────────────────────────

async def run(email: str, password: str, name: str) -> None:
    print(f"\n▸ Seeding demo account: {email}")
    async with httpx.AsyncClient(timeout=60.0) as client:
        user_id = await find_or_create_user(client, email, password, name)
        photos  = await upload_photos(client, user_id)

    conn = await _conn()
    try:
        media_ids = await seed_media(conn, user_id, photos)
        await seed_family(conn, user_id)
        await seed_story(conn, user_id, media_ids)
    finally:
        await conn.close()

    print("\n✓ Done. Sign in with:")
    print(f"    email:    {email}")
    print(f"    password: {password}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email",    default=DEFAULT_EMAIL)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--name",     default=DEFAULT_NAME)
    args = parser.parse_args()

    random.seed(0)   # deterministic output ordering across runs.
    asyncio.run(run(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
