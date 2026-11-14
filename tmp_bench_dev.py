import json
import sys
from pathlib import Path

root = Path('/Users/nguyennamkhanh/Documents/AI In Action/AI20K_Lab/K5-L3A-Day07-NguyenNamKhanh-2A202603398-RetrievalContext')
root_day7 = root / 'src' / 'Day7_INPUT'
sys.path.insert(0, str(root_day7 / 'src'))
sys.path.insert(0, str(root / 'starter'))

from ingestion import load_pdf
from run import build_strategy_chunks, load_benchmark
from starter.agentic import (
    DenseVectorRetrieval,
    LexicalTFIDFRetrieval,
    BM25Retrieval,
    HybridRRFRetrieval,
    QueryExpansionRetrieval,
)

manifest = json.loads((root_day7 / 'data' / 'manifest.json').read_text(encoding='utf-8'))
questions = load_benchmark(root_day7 / 'benchmark' / 'questions.json')
dev = [q for q in questions if q.get('split') == 'dev']
pages = load_pdf(Path(manifest['source_path_or_url']), manifest['document_id'], manifest['title'])
corpus = build_strategy_chunks(manifest['document_id'], manifest['title'], pages, 'A')

methods = {
    'dense': DenseVectorRetrieval(corpus),
    'tfidf': LexicalTFIDFRetrieval(corpus),
    'bm25': BM25Retrieval(corpus),
    'hybrid_rrf': HybridRRFRetrieval(corpus),
    'query_expansion': QueryExpansionRetrieval(corpus),
}

def score_answerable(q, hits):
    gold_page = q.get('gold_page')
    gold_source = q.get('gold_source_id')
    evidence_quote = (q.get('evidence_quote') or '').lower()
    hit1 = False
    ev3 = False
    for h in hits:
        source_ok = gold_source is None or h.get('source') == gold_source or h.get('source_id') == gold_source
        page_ok = gold_page is None or h.get('page') == gold_page
        quote_ok = bool(evidence_quote and evidence_quote in (h.get('text') or '').lower())
        if source_ok and page_ok and not hit1:
            hit1 = True
        if (quote_ok or (source_ok and page_ok)) and not ev3:
            ev3 = True
    return hit1, ev3

for name, retriever in methods.items():
    hit1 = 0
    evidence_hit3 = 0
    total = 0
    for q in dev:
        total += 1
        hits = retriever.search(q['question'], filters=q.get('filter'), top_k=3)
        if q.get('expected_answer') is None:
            ok = not any((h.get('text') or '').strip() and len((h.get('text') or '').strip()) > 20 for h in hits)
            if ok:
                hit1 += 1
                evidence_hit3 += 1
        else:
            h1, h3 = score_answerable(q, hits)
            if h1:
                hit1 += 1
            if h3:
                evidence_hit3 += 1
    print(f'{name}: hit1={hit1}/{total} evidence_hit3={evidence_hit3}/{total} hit1_rate={hit1/total:.2f} ev3_rate={evidence_hit3/total:.2f}')
