import json
import sys
from pathlib import Path

ROOT = Path('/Users/nguyennamkhanh/Documents/AI In Action/AI20K_Lab/K5-L3A-Day07-NguyenNamKhanh-2A202603398-RetrievalContext').resolve()
DAY7 = ROOT / 'src' / 'Day7_INPUT'
sys.path.insert(0, str(DAY7 / 'src'))
sys.path.insert(0, str(ROOT / 'starter'))

from ingestion import load_pdf
from run import build_strategy_chunks, load_benchmark
from starter.agentic import DenseVectorRetrieval

manifest = json.loads((DAY7 / 'data' / 'manifest.json').read_text(encoding='utf-8'))
questions = load_benchmark(DAY7 / 'benchmark' / 'questions.json')
test_questions = [q for q in questions if q.get('split') == 'test']
pages = load_pdf(Path(manifest['source_path_or_url']), manifest['document_id'], manifest['title'])
corpus = build_strategy_chunks(manifest['document_id'], manifest['title'], pages, 'A')
retriever = DenseVectorRetrieval(corpus)


def score(q, hits):
    gold_page = q.get('gold_page')
    gold_source = q.get('gold_source_id')
    evidence_quote = (q.get('evidence_quote') or '').lower()
    hit1 = False
    ev3 = False
    for h in hits:
        h_source = h.get('source') or h.get('source_id')
        source_ok = gold_source is None or h_source == gold_source or h.get('document_id') == gold_source
        page_ok = gold_page is None or h.get('page') == gold_page
        quote_ok = bool(evidence_quote and evidence_quote in (h.get('text') or '').lower())
        if source_ok and page_ok:
            hit1 = True
        if quote_ok or (source_ok and page_ok):
            ev3 = True
    return hit1, ev3

hit1_total = 0
ev3_total = 0
for q in test_questions:
    hits = retriever.search(q['question'], filters=q.get('filter'), top_k=3)
    if q.get('expected_answer') is None:
        ok = not bool([h for h in hits if (h.get('text') or '').strip()])
        if ok:
            hit1_total += 1
            ev3_total += 1
    else:
        h1, h3 = score(q, hits)
        if h1:
            hit1_total += 1
        if h3:
            ev3_total += 1

result = {
    'total': len(test_questions),
    'hit1': hit1_total,
    'evidence_hit3': ev3_total,
    'hit1_rate': round(hit1_total / len(test_questions), 4),
    'evidence_hit3_rate': round(ev3_total / len(test_questions), 4),
}
print(json.dumps(result, ensure_ascii=False))
