import json
import sqlite3
import numpy as np

import config

try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_VECTOR_LIBS = True
except ImportError:
    HAS_VECTOR_LIBS = False


def chunk_words(text: str, size: int = 180, overlap: int = 30) -> list[str]:
    """Split page text into ~180-word chunks with a 30-word overlap."""
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]

    chunks = []
    step = max(1, size - overlap)
    for start in range(0, len(words), step):
        piece = " ".join(words[start : start + size])
        chunks.append(piece)
        if start + size >= len(words):
            break
    return chunks


def init_db(conn: sqlite3.Connection):
    """Create the pages and chunks tables cleanly."""
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS chunks")
    cur.execute("DROP TABLE IF EXISTS pages")

    cur.execute(
        """
        CREATE TABLE pages (
            page_id  TEXT PRIMARY KEY,
            subject  TEXT NOT NULL,
            chapter  TEXT NOT NULL,
            page     INTEGER NOT NULL,
            text     TEXT NOT NULL,
            language TEXT NOT NULL
        )
        """
    )
    cur.execute("CREATE INDEX idx_pages_num_subj ON pages(page, subject)")

    # chunk_id is 0, 1, 2... matching exact row order in the FAISS index
    cur.execute(
        """
        CREATE TABLE chunks (
            chunk_id INTEGER PRIMARY KEY,
            page_id  TEXT NOT NULL,
            text     TEXT NOT NULL,
            FOREIGN KEY (page_id) REFERENCES pages(page_id)
        )
        """
    )
    conn.commit()


def build():
    if not config.PAGES_JSONL.exists():
        raise FileNotFoundError(
            f"{config.PAGES_JSONL} not found. Run `python extract_pages.py` first."
        )

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(config.DB_PATH))
    init_db(conn)
    cur = conn.cursor()

    chunk_texts = []
    page_count = 0
    chunk_id = 0

    with open(config.PAGES_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cur.execute(
                """
                INSERT OR REPLACE INTO pages (page_id, subject, chapter, page, text, language)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["page_id"],
                    rec["subject"].lower(),
                    rec.get("chapter", "General"),
                    int(rec["page"]),
                    rec["text"],
                    rec.get("language", "en"),
                ),
            )
            page_count += 1

            for piece in chunk_words(rec["text"], config.CHUNK_WORDS, config.CHUNK_OVERLAP):
                cur.execute(
                    "INSERT INTO chunks (chunk_id, page_id, text) VALUES (?, ?, ?)",
                    (chunk_id, rec["page_id"], piece),
                )
                chunk_texts.append(piece)
                chunk_id += 1

    conn.commit()
    conn.close()
    print(f"[SQLite] Saved {page_count} pages and {chunk_id} chunks into {config.DB_PATH}")

    if not chunk_texts:
        print("[WARN] No chunks found to embed.")
        return

    if not HAS_VECTOR_LIBS:
        print(
            "[WARN] `sentence-transformers` or `faiss-cpu` not installed in this environment. "
            "SQLite tables are ready; install requirements.txt to build chunks.index."
        )
        return

    print(f"[Embed] Loading {config.EMBED_MODEL_NAME}...")
    model = SentenceTransformer(config.EMBED_MODEL_NAME)
    embeddings = model.encode(
        chunk_texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,  # Normalized vectors + IndexFlatIP = Cosine Similarity
    ).astype("float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, str(config.FAISS_INDEX_PATH))
    print(f"[FAISS] Saved {index.ntotal} vectors (dim={dim}) to {config.FAISS_INDEX_PATH}")


if __name__ == "__main__":
    build()
