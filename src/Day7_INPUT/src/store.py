"""Store and search vectors using PostgreSQL + pgvector."""
from __future__ import annotations

import os
from typing import Any

import psycopg

from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cursor.execute("DROP TABLE IF EXISTS chunks")
                cursor.execute(
                    f"""
                    CREATE TABLE chunks (
                        strategy TEXT NOT NULL,
                        chunk_id TEXT NOT NULL,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INT NOT NULL,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.dimensions}),
                        PRIMARY KEY (strategy, chunk_id)
                    )
                    """
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops)"
                )
                connection.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not chunks:
            return

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                for chunk, vector in zip(chunks, vectors):
                    if len(vector) != self.dimensions:
                        raise ValueError(f"Vector dimension mismatch for chunk {chunk.chunk_id}: expected {self.dimensions}, got {len(vector)}")
                    metadata_json = psycopg.types.json.Json(chunk.metadata)
                    cursor.execute(
                        """
                        INSERT INTO chunks (strategy, chunk_id, document_id, source, page, text, metadata, embedding)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector)
                        ON CONFLICT (strategy, chunk_id)
                        DO UPDATE SET
                            document_id = EXCLUDED.document_id,
                            source = EXCLUDED.source,
                            page = EXCLUDED.page,
                            text = EXCLUDED.text,
                            metadata = EXCLUDED.metadata,
                            embedding = EXCLUDED.embedding
                        """,
                        (
                            strategy,
                            chunk.chunk_id,
                            chunk.document_id,
                            chunk.source,
                            chunk.page,
                            chunk.text,
                            metadata_json,
                            '[' + ','.join(str(v) for v in vector) + ']',
                        ),
                    )
                if chunks:
                    chunk_ids = tuple(chunk.chunk_id for chunk in chunks)
                    placeholders = ', '.join(['%s'] * len(chunk_ids))
                    cursor.execute(
                        f"DELETE FROM chunks WHERE strategy = %s AND chunk_id NOT IN ({placeholders})",
                        (strategy, *chunk_ids),
                    )
                connection.commit()

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        if not query_vector:
            raise ValueError("query_vector cannot be empty")
        if len(query_vector) != self.dimensions:
            raise ValueError(f"query_vector length mismatch: expected {self.dimensions}, got {len(query_vector)}")

        filters = filters or {}
        sql = """
            SELECT chunk_id, document_id, source, page, text, metadata, 1 - (embedding <=> %s::vector) AS score
            FROM chunks
            WHERE strategy = %s
        """
        params: list[Any] = [str(query_vector), strategy]
        filter_clauses: list[str] = []

        for key, value in filters.items():
            if value is None:
                continue
            filter_clauses.append(f"metadata ->> %s = %s")
            params.extend([key, str(value)])

        if filter_clauses:
            sql += " AND " + " AND ".join(filter_clauses)

        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([str(query_vector), top_k])

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()

        return [
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "source": row[2],
                "page": row[3],
                "text": row[4],
                "metadata": row[5],
                "score": float(row[6]),
            }
            for row in rows
        ]


if __name__ == "__main__":
    from pathlib import Path

    db_url = os.getenv("DATABASE_URL", "postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab")
    store = PgVectorStore(db_url, 3)
    store.create_schema()
    print("schema ready")
