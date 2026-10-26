import os
import sqlite3
from typing import Optional, List
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import pipeline
import explainer

app = FastAPI(
    title="PageMate - 10th Standard AI Textbook Companion",
    description="Intelligent RAG assistant, syllabus explorer, textbook viewer, and Gemini AI tutor with full English and Tamil support.",
    version="2.1.0"
)

# Ensure static directory exists and mount it
config.STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(config.STATIC_DIR)), name="static")


def get_db():
    conn = sqlite3.connect(str(config.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def serve_home():
    """Serve index.html at root."""
    template_file = config.BASE_DIR / "templates" / "index.html"
    if template_file.exists():
        return FileResponse(str(template_file))
    return FileResponse(str(config.STATIC_DIR / "index.html"))


@app.get("/api/ask")
def ask(
    q: str = Query(..., min_length=1, description="Student query e.g. 'explain pg:100' or 'reflex action'"),
    lang: str = Query("en", pattern="^(en|ta)$", description="Output language: 'en' (English) or 'ta' (Tamil)"),
):
    """
    Main RAG endpoint:
      1. Resolve query via pipeline.resolve(q)
      2. If status == 'choose' or 'not_found', return structured payload in requested language
      3. For retrieved pages, generate grounded explanation in requested language ('en' or 'ta')
    """
    resolved = pipeline.resolve(q)
    status = resolved["status"]

    if status == "choose":
        msg = (
            f"பக்கம் {resolved['parsed']['page']} பல பாடங்களில் உள்ளது. தயவுசெய்து உங்கள் பாடத்தைத் தேர்ந்தெடுக்கவும்:"
            if lang == "ta"
            else f"Page {resolved['parsed']['page']} exists in multiple subjects. Please select your subject:"
        )
        return {
            "status": "choose",
            "query": q,
            "page": resolved["parsed"]["page"],
            "subjects": resolved["subjects"],
            "message": msg,
            "results": [],
        }

    if status == "not_found":
        msg = (
            "பொருத்தமான பாடநூல் பக்கம் எதுவும் கிடைக்கவில்லை. பக்க எண்ணை சரிபார்க்கவும் அல்லது மற்றொரு தலைப்புச் சொல்லை முயற்சிக்கவும்."
            if lang == "ta"
            else "No matching textbook page found. Try a different page number or topic keyword."
        )
        return {
            "status": "not_found",
            "query": q,
            "message": msg,
            "results": [],
        }

    results = []
    for page_rec in resolved["pages"]:
        exp = explainer.explain_page(page_rec, lang=lang, user_query=q)
        results.append(
            {
                "page_id": page_rec["page_id"],
                "subject": page_rec["subject"],
                "chapter": page_rec["chapter"],
                "page": page_rec["page"],
                "language": page_rec["language"],
                "score": page_rec.get("score"),
                "explanation": exp["explanation"],
                "used_fallback": exp["used_fallback"],
                "source_text": page_rec["text"],
            }
        )

    return {
        "status": "ok",
        "mode": resolved["mode"],
        "query": q,
        "lang": lang,
        "results": results,
    }


@app.get("/api/syllabus")
def get_syllabus():
    """
    Returns complete 10th standard syllabus breakdown:
    Subjects, chapters, page ranges, and total pages count.
    """
    if not config.DB_PATH.exists():
        return {"subjects": [], "total_pages": 0}

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM pages")
    total_pages = cur.fetchone()[0]

    cur.execute("SELECT DISTINCT subject FROM pages ORDER BY subject")
    subject_rows = cur.fetchall()

    syllabus_data = []
    for s_row in subject_rows:
        subj = s_row["subject"]
        cur.execute(
            """
            SELECT chapter, MIN(page) as start_page, MAX(page) as end_page, COUNT(page_id) as page_count
            FROM pages
            WHERE subject = ?
            GROUP BY chapter
            ORDER BY MIN(page)
            """,
            (subj,)
        )
        chaps = [dict(c) for c in cur.fetchall()]
        cur.execute("SELECT COUNT(page_id), MIN(page), MAX(page) FROM pages WHERE subject = ?", (subj,))
        stats = cur.fetchone()

        syllabus_data.append({
            "subject": subj,
            "display_name": subj.title(),
            "total_pages": stats[0],
            "page_range": f"{stats[1]} - {stats[2]}",
            "chapter_count": len(chaps),
            "chapters": chaps
        })

    conn.close()
    return {"subjects": syllabus_data, "total_pages": total_pages}


@app.get("/api/page")
def get_single_page(
    subject: str = Query(..., description="Subject name e.g. science"),
    page: int = Query(..., ge=1, le=1000, description="Page number"),
):
    """
    Directly view a single textbook page and its adjacent pages for context.
    """
    if not config.DB_PATH.exists():
        return JSONResponse(status_code=404, content={"error": "Database not initialized"})

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT page_id, subject, chapter, page, text, language FROM pages WHERE LOWER(subject) = LOWER(?) AND page = ?",
        (subject.strip(), int(page))
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return JSONResponse(status_code=404, content={"error": f"Page {page} not found in {subject}"})

    current_page = dict(row)

    cur.execute(
        "SELECT page FROM pages WHERE LOWER(subject) = LOWER(?) AND page = ?",
        (subject.strip(), int(page) - 1)
    )
    has_prev = cur.fetchone() is not None

    cur.execute(
        "SELECT page FROM pages WHERE LOWER(subject) = LOWER(?) AND page = ?",
        (subject.strip(), int(page) + 1)
    )
    has_next = cur.fetchone() is not None

    conn.close()
    return {
        "page": current_page,
        "has_prev": has_prev,
        "has_next": has_next,
    }


class ChatMessage(BaseModel):
    role: str
    text: str


class TutorChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    lang: Optional[str] = "en"
    subject: Optional[str] = None


@app.post("/api/tutor")
def chat_with_tutor(req: TutorChatRequest):
    """
    Interactive Gemini AI Tutor endpoint.
    Passes requested language ('en' or 'ta') directly down to explainer.tutor_chat.
    """
    history_dicts = [{"role": h.role, "text": h.text} for h in (req.history or [])]
    target_lang = "ta" if (req.lang and req.lang.lower() == "ta") else "en"
    res = explainer.tutor_chat(
        message=req.message,
        history=history_dicts,
        lang=target_lang,
        subject=req.subject,
    )
    return res


@app.get("/api/health")
def health_check():
    """System health check and vector store status."""
    has_db = config.DB_PATH.exists()
    has_index = config.FAISS_INDEX_PATH.exists()
    return {
        "status": "healthy",
        "database_exists": has_db,
        "faiss_index_exists": has_index,
        "has_gemini_key": bool(getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY")),
        "model": getattr(config, "GEMINI_MODEL_NAME", "gemini-2.5-flash"),
    }
