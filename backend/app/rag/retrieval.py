import hashlib
import math
import re

from pgvector.sqlalchemy import Vector
from sqlalchemy import cast, select
from sqlalchemy.orm import Session

from app.models.entities import KnowledgeChunk, KnowledgeDocument

DIMENSIONS = 64


def embed(text: str) -> list[float]:
    """Stable local hashing embedding. Useful for demos, not semantic production search."""
    vector = [0.0] * DIMENSIONS
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        slot = int.from_bytes(digest[:4], "big") % DIMENSIONS
        vector[slot] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def chunks(content: str, size: int = 700, overlap: int = 100) -> list[str]:
    return [content[i : i + size] for i in range(0, len(content), size - overlap)]


def ingest(db: Session, title: str, content: str, source: str) -> KnowledgeDocument:
    if not content.strip() or len(content) > 100_000:
        raise ValueError("Document must contain 1 to 100,000 characters")
    document = KnowledgeDocument(title=title, content=content, source=source)
    db.add(document)
    db.flush()
    for ordinal, piece in enumerate(chunks(content)):
        db.add(
            KnowledgeChunk(
                document_id=document.id, ordinal=ordinal, content=piece, embedding=embed(piece)
            )
        )
    db.commit()
    db.refresh(document)
    return document


def retrieve(db: Session, query: str, limit: int = 3) -> list[dict]:
    vector = embed(query)
    if db.bind and db.bind.dialect.name == "postgresql":
        distance = cast(KnowledgeChunk.embedding, Vector(DIMENSIONS)).cosine_distance(vector)
        rows = db.execute(
            select(KnowledgeChunk, KnowledgeDocument, distance.label("distance"))
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .order_by(distance)
            .limit(limit)
        ).all()
        return [
            {
                "score": round(max(0.0, 1.0 - float(dist)), 3),
                "title": doc.title,
                "source": doc.source,
                "excerpt": chunk.content,
                "document_id": doc.id,
            }
            for chunk, doc, dist in rows
            if dist is not None and dist < 1
        ]
    matches = db.execute(
        select(KnowledgeChunk, KnowledgeDocument).join(
            KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id
        )
    ).all()
    scored = [
        (sum(a * b for a, b in zip(vector, chunk.embedding)), chunk, document)
        for chunk, document in matches
    ]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "score": round(score, 3),
            "title": doc.title,
            "source": doc.source,
            "excerpt": chunk.content,
            "document_id": doc.id,
        }
        for score, chunk, doc in scored[:limit]
        if score > 0
    ]
