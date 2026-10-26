import sqlite3
import config

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_VECTOR_LIBS = True
except ImportError:
    HAS_VECTOR_LIBS = False

_embed_model = None
_faiss_index = None


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _load_vector_resources():
    """Lazy-load SentenceTransformer and FAISS index once per process."""
    global _embed_model, _faiss_index
    if not HAS_VECTOR_LIBS:
        return None, None
    if _embed_model is None:
        _embed_model = SentenceTransformer(config.EMBED_MODEL_NAME)
    if _faiss_index is None and config.FAISS_INDEX_PATH.exists():
        _faiss_index = faiss.read_index(str(config.FAISS_INDEX_PATH))
    return _embed_model, _faiss_index


def get_pages(page: int, subject: str | None = None) -> list[dict]:
    """
    Exact SQLite lookup by printed page number (and optional subject).
    NEVER uses the LLM or vector search.
    """
    if not config.DB_PATH.exists():
        return []

    conn = _get_conn()
    cur = conn.cursor()
    if subject:
        cur.execute(
            "SELECT page_id, subject, chapter, page, text, language FROM pages WHERE page = ? AND LOWER(subject) = LOWER(?)",
            (int(page), subject.strip()),
        )
    else:
        cur.execute(
            "SELECT page_id, subject, chapter, page, text, language FROM pages WHERE page = ? ORDER BY subject",
            (int(page),),
        )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def topic_search(query_text: str, subject: str | None = None, k: int = config.TOP_K_PAGES) -> list[dict]:
    """
    Embed the topic query, search the FAISS cosine index, and return the top 1 to k unique pages.
    """
    if not query_text or not config.DB_PATH.exists():
        return []

    model, index = _load_vector_resources()
    conn = _get_conn()
    cur = conn.cursor()

    # Standard FAISS vector similarity search
    if model is not None and index is not None and index.ntotal > 0:
        q_vec = model.encode(
            [query_text],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).astype("float32")

        # Over-fetch chunks (k * 6) so deduplicating by page_id still yields k distinct pages
        search_k = min(index.ntotal, max(k * 6, 15))
        scores, chunk_ids = index.search(q_vec, search_k)

        seen_pages = set()
        results = []

        for score, cid in zip(scores[0], chunk_ids[0]):
            if cid < 0:
                continue
            cur.execute(
                """
                SELECT p.page_id, p.subject, p.chapter, p.page, p.text, p.language
                FROM chunks c
                JOIN pages p ON p.page_id = c.page_id
                WHERE c.chunk_id = ?
                """,
                (int(cid),),
            )
            row = cur.fetchone()
            if not row:
                continue
            page_dict = dict(row)
            if subject and page_dict["subject"].lower() != subject.lower():
                continue
            if page_dict["page_id"] in seen_pages:
                continue

            seen_pages.add(page_dict["page_id"])
            page_dict["score"] = round(float(score), 4)
            results.append(page_dict)
            if len(results) >= k:
                break

        conn.close()
        return results

    # Fallback keyword matching ONLY if FAISS index hasn't been built yet
    words = [w for w in query_text.lower().split() if len(w) >= 3]
    if not words:
        conn.close()
        return []

    sql = "SELECT page_id, subject, chapter, page, text, language FROM pages"
    params = []
    if subject:
        sql += " WHERE LOWER(subject) = LOWER(?)"
        params.append(subject)

    cur.execute(sql, params)
    scored = []
    for r in cur.fetchall():
        d = dict(r)
        hay = d["text"].lower()
        hits = sum(hay.count(w) for w in words)
        if hits > 0:
            d["score"] = float(hits)
            scored.append(d)

    conn.close()
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
