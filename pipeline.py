import query_parser
import retriever
import config


def resolve(raw_query: str) -> dict:
    """
    Resolve a student query and return a dict with:
      - status: "ok" | "choose" | "not_found"
      - mode: "page" | "topic"
      - parsed: dict from query_parser
      - subjects: list of matching subjects (when status == "choose")
      - pages: list of matching page dicts (when status == "ok")
    """
    parsed = query_parser.parse_query(raw_query)
    page_num = parsed["page"]
    subject = parsed["subject"]
    topic = parsed["topic"]

    # Route 1: Query contains a page number -> exact SQLite lookup ONLY (no AI/vector search)
    if page_num is not None:
        matches = retriever.get_pages(page_num, subject)
        if not matches:
            return {
                "status": "not_found",
                "mode": "page",
                "parsed": parsed,
                "subjects": [],
                "pages": [],
            }

        # If the same page number exists in multiple subjects and no subject was given, ask student
        unique_subjects = sorted({m["subject"] for m in matches})
        if len(unique_subjects) > 1 and not subject:
            return {
                "status": "choose",
                "mode": "page",
                "parsed": parsed,
                "subjects": unique_subjects,
                "pages": [],
            }

        return {
            "status": "ok",
            "mode": "page",
            "parsed": parsed,
            "subjects": unique_subjects,
            "pages": matches,
        }

    # Route 2: Topic query -> FAISS vector search
    search_text = topic or raw_query.strip()
    if not search_text:
        return {
            "status": "not_found",
            "mode": "topic",
            "parsed": parsed,
            "subjects": [],
            "pages": [],
        }

    matches = retriever.topic_search(search_text, subject=subject, k=config.TOP_K_PAGES)
    if not matches:
        return {
            "status": "not_found",
            "mode": "topic",
            "parsed": parsed,
            "subjects": [],
            "pages": [],
        }

    return {
        "status": "ok",
        "mode": "topic",
        "parsed": parsed,
        "subjects": sorted({m["subject"] for m in matches}),
        "pages": matches,
    }
