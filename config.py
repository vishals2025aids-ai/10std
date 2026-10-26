# config.py - Central settings for PageMate
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent
BOOKS_DIR = BASE_DIR / "books"
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"

PAGES_JSONL = DATA_DIR / "pages.jsonl"
DB_PATH = DATA_DIR / "pagemate.db"
FAISS_INDEX_PATH = DATA_DIR / "chunks.index"
TESTS_CSV = BASE_DIR / "tests.csv"

# Pre-trained model names
# Multilingual MiniLM supports both English and Tamil queries out of the box
EMBED_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
# Current recommended fast Gemini model via google-genai SDK
GEMINI_MODEL_NAME = "gemini-2.5-flash"

# Chunking and OCR settings
CHUNK_WORDS = 180
CHUNK_OVERLAP = 30
MIN_CHARS_FOR_TEXT = 40  # Below 40 characters -> run Tesseract OCR fallback
TOP_K_PAGES = 3          # Max pages returned for a topic search

# Windows paths for Tesseract & Poppler (update if installed in custom folders on Windows)
# Example: r"C:\Program Files\Tesseract-OCR	esseract.exe"
TESSERACT_CMD = None
POPPLER_PATH = None

# Books configuration
# Start with ONE subject (Science) first, then uncomment the rest once verified!
# 'offset' is the number of preliminary PDF pages (cover, preface, contents) before printed page 1.
# Formula: printed_page = pdf_page_number (1-based) - offset
BOOKS = {
    "10th_Science.pdf": {
        "subject": "science",
        "offset": 8,       # Adjust to match your PDF (e.g., if printed page 1 is PDF page 9, offset = 8)
        "language": "en",
    },
    # Uncomment and adjust offsets after Science is tested and working:
    # "10th_Maths.pdf":        {"subject": "maths",   "offset": 6, "language": "en"},
    # "10th_Social.pdf":       {"subject": "social",  "offset": 8, "language": "en"},
    # "10th_English.pdf":      {"subject": "english", "offset": 6, "language": "en"},
    # "10th_Tamil.pdf":        {"subject": "tamil",   "offset": 6, "language": "ta"},
}

# Subject keyword aliases (English + Tamil) used by query_parser.py
SUBJECT_ALIASES = {
    "science": ["science", "sci", "physics", "chemistry", "biology", "அறிவியல்"],
    "maths": ["maths", "math", "mathematics", "geometry", "algebra", "கணிதம்"],
    "social": ["social", "history", "geography", "civics", "economics", "சமூக அறிவியல்", "வரலாறு", "புவியியல்"],
    "english": ["english", "eng", "ஆங்கிலம்"],
    "tamil": ["tamil", "tam", "தமிழ்"],
}
