"""Choose a real embedding provider. The default implementation uses TF-IDF vectors so the lab can run locally without API keys."""
from __future__ import annotations

from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, question: str) -> list[float]:
        ...


class MyEmbedder:
    """Real vectorizer-based embedder that works in local labs without external API keys.

    This intentionally uses TF-IDF as a local fallback for reproducibility in a course lab.
    """

    def __init__(self, model_name: str = "tfidf-local") -> None:
        self.model_name = model_name
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=2000)
        self.dimensions = 0

    def fit(self, texts: list[str]) -> None:
        if not texts:
            raise ValueError("At least one text is required to fit the embedder")
        self.vectorizer.fit(texts)
        self.dimensions = len(self.vectorizer.vocabulary_)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if not hasattr(self.vectorizer, "vocabulary_") or not self.vectorizer.vocabulary_:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts)
        vectors = matrix.toarray().astype(float)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, question: str) -> list[float]:
        if not hasattr(self.vectorizer, "vocabulary_") or not self.vectorizer.vocabulary_:
            raise ValueError("The embedder must be fitted before embedding a query.")
        vector = self.vectorizer.transform([question]).toarray()[0].astype(float)
        return vector.tolist()


if __name__ == "__main__":
    embedder = MyEmbedder()
    texts = ["software engineering requires clear design", "testing helps confidence"]
    print(embedder.embed_documents(texts))
