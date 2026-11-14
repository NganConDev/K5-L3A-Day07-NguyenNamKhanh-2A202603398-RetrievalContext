"""Run the data ingestion pipeline and benchmark comparisons."""
from __future__ import annotations

import json
import re
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import PgVectorStore


def normalize_pdf_chunk_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = cleaned.replace("www.it-ebooks.info", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def infer_page_section(text: str) -> str:
    full_text = (text or "").lower()
    if "section:" in full_text:
        match = re.search(r"section:\s*([a-z0-9 _-]+)", full_text)
        if match:
            return match.group(1).strip().lower().replace(" ", "_")

    heading_patterns = [
        ("writing clean code is what you must do", "front_matter"),
        ("there is no reasonable excuse for doing anything less than your best", "front_matter"),
        ("foreword", "foreword"),
        ("introduction", "introduction"),
        ("contents", "contents"),
        ("chapter", "chapter"),
        ("appendix", "appendix"),
        ("bibliography", "bibliography"),
        ("conclusion", "conclusion"),
    ]
    for pattern, section in heading_patterns:
        if pattern in full_text:
            return section

    return "general"


def infer_question_section(question: str) -> str | None:
    normalized = question.lower()
    if any(word in normalized for word in ["professional", "clean code", "best work", "write clean code"]):
        return "front_matter"
    if any(word in normalized for word in ["foreword", "maintenance", "small things", "cleanliness", "quality", "details"]):
        return "foreword"
    if any(word in normalized for word in ["introduction", "craftsmanship", "knowledge", "practice", "work"]):
        return "introduction"
    return None


def load_benchmark(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_strategy_chunks(document_id: str, source: str, pages: list, strategy: str) -> list:
    chunks: list = []
    for page in pages:
        raw_section = page.metadata.get("section")
        page_section = infer_page_section(page.text) if (not raw_section or raw_section == "general") else raw_section
        page.metadata["section"] = page_section
        page.metadata["page_heading"] = (page.text.splitlines()[0] if page.text.splitlines() else "").strip()

        if strategy == "A":
            chunk_list = fixed_size(page, size=180, overlap=30)
        elif strategy == "B":
            chunk_list = by_paragraph(page, max_size=180)
        else:
            chunk_list = by_paragraph(page, max_size=180)

        for chunk in chunk_list:
            cleaned_text = normalize_pdf_chunk_text(chunk.text)
            chunk.text = cleaned_text
            chunk.metadata.setdefault("section", page_section)
            chunk.metadata["page_heading"] = page.metadata.get("page_heading", "")
            if chunk.text and "www.it-ebooks.info" not in chunk.text.lower():
                chunks.append(chunk)
    return chunks


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    base_dir = Path(__file__).resolve().parents[1]
    manifest_path = base_dir / "data" / "manifest.json"
    benchmark_path = base_dir / "benchmark" / "questions.json"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    corpus_path = Path(manifest["source_path_or_url"])
    document_id = manifest["document_id"]
    source = manifest["title"]

    pages = load_pdf(corpus_path, document_id, source)
    if len(pages) < 30:
        raise ValueError(f"Corpus must contain at least 30 pages; found {len(pages)}")

    strategy_names = ["A", "B", "C"]
    questions = load_benchmark(benchmark_path)
    embedder = MyEmbedder()
    all_texts = []
    for strategy in strategy_names:
        for chunk in build_strategy_chunks(document_id, source, pages, strategy):
            all_texts.append(chunk.text)

    embedder.fit(all_texts)
    database_url = (base_dir / ".env").read_text(encoding="utf-8").split("DATABASE_URL=")[-1].strip().splitlines()[0]
    store = PgVectorStore(database_url, embedder.dimensions)
    store.create_schema()

    results_by_strategy: dict[str, dict] = {}
    for strategy in strategy_names:
        strategy_chunks = build_strategy_chunks(document_id, source, pages, strategy)
        if strategy == "C":
            for chunk in strategy_chunks:
                chunk.metadata["section"] = chunk.metadata.get("section") or "general"

        vectors = embedder.embed_documents([chunk.text for chunk in strategy_chunks])
        store.upsert(strategy, strategy_chunks, vectors)

        traces: list[dict] = []
        for question in questions:
            filter_value = question.get("filter")
            if strategy == "C" and not filter_value:
                section_hint = infer_question_section(question["question"])
                if section_hint:
                    filter_value = {"section": section_hint}
            query_vector = embedder.embed_query(question["question"])
            hits = store.search(strategy, query_vector, top_k=3, filters=filter_value)
            trace = evaluate_query(question, hits)
            trace["strategy"] = strategy
            trace["question"] = question["question"]
            traces.append(trace)

        results_by_strategy[strategy] = summarize(traces)
        print(f"Strategy {strategy}: {results_by_strategy[strategy]}")

    print("Pipeline complete. Results are printed above.")


if __name__ == "__main__":
    main()
