import json
import sys
from pathlib import Path

ROOT = Path('/Users/nguyennamkhanh/Documents/AI In Action/AI20K_Lab/K5-L3A-Day07-NguyenNamKhanh-2A202603398-RetrievalContext')
DAY7 = ROOT / 'src' / 'Day7_INPUT'
sys.path.insert(0, str(DAY7 / 'src'))
sys.path.insert(0, str(ROOT / 'starter'))

from ingestion import load_pdf
from run import build_strategy_chunks, load_benchmark
from starter.agentic import (
    DenseVectorRetrieval,
    LexicalTFIDFRetrieval,
    BM25Retrieval,
    HybridRRFRetrieval,
    QueryExpansionRetrieval,
)

manifest = json.loads((DAY7 / 'data' / 'manifest.json').read_text(encoding='utf-8'))
questions = load_benchmark(DAY7 / 'benchmark' / 'questions.json')
dev_questions = [q for q in questions if q.get('split') == 'dev']

pages = load_pdf(Path(manifest['source_path_or_url']), manifest['document_id'], manifest['title'])
corpus = build_strategy_chunks(manifest['document_id'], manifest['title'], pages, 'A')

methods = {
    'dense': DenseVectorRetrieval(corpus),
    'tfidf': LexicalTFIDFRetrieval(corpus),
    'bm25': BM25Retrieval(corpus),
    'hybrid_rrf': HybridRRFRetrieval(corpus),
    'query_expansion': QueryExpansionRetrieval(corpus),
}

def score(q, hits):
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

results = []
for name, retriever in methods.items():
    hit1 = 0
    ev3 = 0
    total = len(dev_questions)
    for q in dev_questions:
        hits = retriever.search(q['question'], filters=q.get('filter'), top_k=3)
        if q.get('expected_answer') is None:
            ok = not any((h.get('text') or '').strip() and len((h.get('text') or '').strip()) > 20 for h in hits)
            if ok:
                hit1 += 1
                ev3 += 1
        else:
            h1, h3 = score(q, hits)
            if h1:
                hit1 += 1
            if h3:
                ev3 += 1
    results.append((name, hit1, ev3, total))

for name, hit1, ev3, total in results:
    print(f'{name}: hit1={hit1}/{total} evidence_hit3={ev3}/{total} hit1_rate={hit1/total:.2f} ev3_rate={ev3/total:.2f}')
