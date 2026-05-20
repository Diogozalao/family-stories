"""
Sistema RAG (Retrieval-Augmented Generation).

Como funciona (modo cheio, com ChromaDB instalado):
1. Todos os factos extraídos pelo M1/M2 são guardados numa base vetorial
2. Quando o LLM precisa de gerar uma narrativa, o RAG pesquisa os factos relevantes
3. Apenas esses factos são injetados no prompt — evita alucinações

Modo degradado (sem ChromaDB — usado no deploy do Render, onde o
chromadb tem um custo de build inviável para o free tier):
   * ``index_media``/``index_events`` viram no-ops
   * ``search`` devolve sempre ``[]`` — o M3 ainda funciona, apenas
     deixa de ter o passo de retrieval e usa todos os factos como contexto.

Isolamento multi-tenant: cada documento traz ``user_id`` na metadata,
e ``search()`` filtra por esse campo.
"""

import structlog

from backend.core.config import settings

log = structlog.get_logger()

# Try to import chromadb at module load time. When the wheel isn't
# available (deployment images, low-memory hosts) we still let the rest
# of M3 load — the RAGSystem just becomes a stub.
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except Exception as _exc:                      # noqa: BLE001
    chromadb = None                            # type: ignore[assignment]
    _CHROMA_AVAILABLE = False
    log.info("rag_chromadb_unavailable", reason=str(_exc))


def _uid(user_id) -> str:
    """Normaliza UUID/str para a string usada nos filtros do Chroma."""
    return str(user_id)


class RAGSystem:
    def __init__(self):
        if not _CHROMA_AVAILABLE:
            self.client = None
            self.collection = None
            log.info("rag_ready", mode="stub")
            return

        db_path = settings.PROCESSED_DIR / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(
            name="family_facts",
            metadata={"description": "Factos familiares extraídos pelo M1 e M2"}
        )
        log.info("rag_ready", path=str(db_path))

    def index_media(self, media_list: list) -> int:
        """Indexa todos os media processados pelo M1.

        Cada media só é indexado uma vez por owner e o seu ``user_id`` fica
        na metadata — ``search`` filtra por aí.
        """
        if self.collection is None:
            return 0
        documents = []
        metadatas = []
        ids       = []

        for media in media_list:
            parts = []
            if media.ai_description:
                parts.append(f"Descrição: {media.ai_description}")
            if media.ai_setting:
                parts.append(f"Local: {media.ai_setting}")
            if media.ai_emotion:
                parts.append(f"Emoção: {media.ai_emotion}")
            if media.ai_tags:
                parts.append(f"Tags: {', '.join(media.ai_tags)}")
            if media.ai_narrative_hint:
                parts.append(f"Sugestão narrativa: {media.ai_narrative_hint}")
            if media.ocr_text:
                parts.append(f"Texto no documento: {media.ocr_text[:500]}")
            if media.date_taken:
                parts.append(f"Data: {media.date_taken.strftime('%d/%m/%Y')}")
            if media.location_name:
                parts.append(f"Localização: {media.location_name}")

            if not parts:
                continue

            doc_id  = f"media_{media.id}"
            text    = " | ".join(parts)
            user_id = _uid(media.user_id)

            metadata = {
                "user_id":    user_id,
                "media_id":   media.id,
                "media_type": str(media.media_type),
                "date":       str(media.date_taken) if media.date_taken else "",
                "emotion":    media.ai_emotion or "",
            }

            existing = self.collection.get(ids=[doc_id])
            if existing["ids"]:
                self.collection.update(ids=[doc_id], documents=[text], metadatas=[metadata])
            else:
                documents.append(text)
                metadatas.append(metadata)
                ids.append(doc_id)

        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            log.info("rag_indexed", count=len(documents))

        return len(documents)

    def index_events(self, events: list) -> int:
        """Indexa eventos da timeline do M2 (carrega user_id na metadata)."""
        if self.collection is None:
            return 0
        documents = []
        metadatas = []
        ids       = []

        for event in events:
            parts = []
            if event.title:
                parts.append(f"Evento: {event.title}")
            if event.description:
                parts.append(f"Descrição: {event.description}")
            if event.event_type:
                parts.append(f"Tipo: {event.event_type}")
            if event.location:
                parts.append(f"Local: {event.location}")
            if event.date_label:
                parts.append(f"Data: {event.date_label}")

            if not parts:
                continue

            doc_id   = f"event_{event.id}"
            text     = " | ".join(parts)
            user_id  = _uid(event.user_id)
            metadata = {"user_id": user_id, "event_id": event.id, "type": event.event_type or ""}

            existing = self.collection.get(ids=[doc_id])
            if existing["ids"]:
                self.collection.update(ids=[doc_id], documents=[text], metadatas=[metadata])
            else:
                documents.append(text)
                metadatas.append(metadata)
                ids.append(doc_id)

        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            log.info("rag_events_indexed", count=len(documents))

        return len(documents)

    def search(self, query: str, user_id, n_results: int = 5) -> list[str]:
        """Pesquisa os factos mais relevantes para uma query, restrita ao owner."""
        if self.collection is None or self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts = [query],
            n_results   = min(n_results, self.collection.count()),
            where       = {"user_id": _uid(user_id)},
        )
        return results["documents"][0] if results["documents"] else []

    def get_all_facts(self, user_id, limit: int = 20) -> list[str]:
        """Retorna factos indexados pelo owner (até ``limit``)."""
        if self.collection is None or self.collection.count() == 0:
            return []
        results = self.collection.get(limit=limit, where={"user_id": _uid(user_id)})
        return results["documents"] if results["documents"] else []

    def count_for(self, user_id) -> int:
        """Quantos factos indexados pertencem ao owner."""
        if self.collection is None:
            return 0
        results = self.collection.get(where={"user_id": _uid(user_id)})
        return len(results["ids"]) if results.get("ids") else 0

    @property
    def total_facts(self) -> int:
        """Total global — usado para diagnóstico, não exposto a users."""
        if self.collection is None:
            return 0
        return self.collection.count()
