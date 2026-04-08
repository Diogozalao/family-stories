"""
Sistema RAG (Retrieval-Augmented Generation).

Como funciona:
1. Todos os factos extraídos pelo M1/M2 são guardados numa base de dados vetorial (ChromaDB)
2. Quando o LLM precisa de gerar uma narrativa, o RAG pesquisa os factos mais relevantes
3. Apenas esses factos são injetados no prompt — evita alucinações

É como dar ao LLM uma "pasta de documentos" específica antes de escrever.
"""

import chromadb
import structlog
from pathlib import Path
from backend.core.config import settings

log = structlog.get_logger()


class RAGSystem:
    def __init__(self):
        db_path = settings.PROCESSED_DIR / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(path=str(db_path))
        self.collection = self.client.get_or_create_collection(
            name="family_facts",
            metadata={"description": "Factos familiares extraídos pelo M1 e M2"}
        )
        log.info("rag_ready", path=str(db_path))

    def index_media(self, media_list: list) -> int:
        """
        Indexa todos os media processados pelo M1.
        Cada media torna-se um 'documento' pesquisável.
        """
        documents = []
        metadatas = []
        ids       = []

        for media in media_list:
            # Constrói texto pesquisável com todos os factos do media
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

            doc_id = f"media_{media.id}"
            text   = " | ".join(parts)

            # Evita duplicados
            existing = self.collection.get(ids=[doc_id])
            if existing["ids"]:
                self.collection.update(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[{
                        "media_id":   media.id,
                        "media_type": str(media.media_type),
                        "date":       str(media.date_taken) if media.date_taken else "",
                        "emotion":    media.ai_emotion or "",
                    }]
                )
            else:
                documents.append(text)
                metadatas.append({
                    "media_id":   media.id,
                    "media_type": str(media.media_type),
                    "date":       str(media.date_taken) if media.date_taken else "",
                    "emotion":    media.ai_emotion or "",
                })
                ids.append(doc_id)

        if documents:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            log.info("rag_indexed", count=len(documents))

        return len(documents)

    def index_events(self, events: list) -> int:
        """Indexa os eventos da timeline do M2."""
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

            doc_id = f"event_{event.id}"
            text   = " | ".join(parts)

            existing = self.collection.get(ids=[doc_id])
            if existing["ids"]:
                self.collection.update(ids=[doc_id], documents=[text],
                    metadatas=[{"event_id": event.id, "type": event.event_type or ""}])
            else:
                documents.append(text)
                metadatas.append({"event_id": event.id, "type": event.event_type or ""})
                ids.append(doc_id)

        if documents:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
            log.info("rag_events_indexed", count=len(documents))

        return len(documents)

    def search(self, query: str, n_results: int = 5) -> list[str]:
        """
        Pesquisa os factos mais relevantes para uma query.
        Ex: query="casamento família" → devolve factos sobre casamentos
        """
        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(n_results, self.collection.count()),
        )

        return results["documents"][0] if results["documents"] else []

    def get_all_facts(self, limit: int = 20) -> list[str]:
        """Retorna todos os factos indexados (para narrativas completas)."""
        if self.collection.count() == 0:
            return []

        results = self.collection.get(limit=limit)
        return results["documents"] if results["documents"] else []

    @property
    def total_facts(self) -> int:
        return self.collection.count()
