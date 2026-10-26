import json
import re
from pypdf import PdfReader
import pytesseract
from pdf2image import convert_from_path

import config

# Optional Windows binary path setup
if config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD


def clean_text(raw: str) -> str:
    """Normalize whitespace and strip noisy control characters."""
    if not raw:
        return ""
    # Replace multiple spaces/tabs with a single space
    text = re.sub(r"[ \t]+", " ", raw)
    # Collapse 3+ newlines into 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_chapter(text: str, current_chapter: str) -> str:
    """Look for 'Unit X' or 'Chapter X' headings near the top of a page."""
    first_lines = "\n".join(text.splitlines()[:8])
    match = re.search(
        r"\b(Unit|Chapter|Lesson|அலகு|பாடம்)\s*[-:]?\s*(\d+[A-Za-z0-9\s:.-]{0,50})",
        first_lines,
        re.IGNORECASE,
    )
    if match:
        heading = f"{match.group(1).title()} {match.group(2).strip()}"
        # Keep only the first line of the matched heading
        return heading.splitlines()[0].strip()
    return current_chapter


def ocr_single_page(pdf_path, pdf_page_1based: int) -> str:
    """Render a single scanned PDF page to an image and run Tesseract (eng+tam)."""
    try:
        kwargs = {"first_page": pdf_page_1based, "last_page": pdf_page_1based, "dpi": 200}
        if config.POPPLER_PATH:
            kwargs["poppler_path"] = config.POPPLER_PATH
        images = convert_from_path(str(pdf_path), **kwargs)
        if not images:
            return ""
        raw_ocr = pytesseract.image_to_string(images[0], lang="eng+tam")
        return clean_text(raw_ocr)
    except Exception as exc:
        print(f"  [WARN] OCR failed on {pdf_path.name} PDF page {pdf_page_1based}: {exc}")
        return ""


def process_books():
    """Loop over configured PDFs and write one JSON record per printed page."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    config.BOOKS_DIR.mkdir(parents=True, exist_ok=True)

    total_written = 0
    with open(config.PAGES_JSONL, "w", encoding="utf-8") as out_f:
        for filename, meta in config.BOOKS.items():
            pdf_path = config.BOOKS_DIR / filename
            if not pdf_path.exists():
                print(f"[SKIP] {pdf_path} not found. Place the PDF in {config.BOOKS_DIR} first.")
                continue

            subject = meta["subject"].lower()
            offset = int(meta.get("offset", 0))
            language = meta.get("language", "en")

            print(f"[INFO] Reading {filename} (subject={subject}, offset={offset})...")
            reader = PdfReader(str(pdf_path))
            current_chapter = "General"

            for idx, page_obj in enumerate(reader.pages):
                pdf_page_num = idx + 1
                printed_page = pdf_page_num - offset

                # Skip cover, preface, and table of contents before printed page 1
                if printed_page < 1:
                    continue

                raw_text = page_obj.extract_text() or ""
                text = clean_text(raw_text)

                # Scanned page check: if fewer than 40 characters, fall back to OCR
                if len(text) < config.MIN_CHARS_FOR_TEXT:
                    print(f"  [OCR] Page {printed_page} (PDF p.{pdf_page_num}) has {len(text)} chars -> running OCR...")
                    ocr_text = ocr_single_page(pdf_path, pdf_page_num)
                    if len(ocr_text) > len(text):
                        text = ocr_text

                if not text:
                    continue

                current_chapter = detect_chapter(text, current_chapter)
                page_id = f"{subject}_p{printed_page}"

                record = {
                    "page_id": page_id,
                    "subject": subject,
                    "chapter": current_chapter,
                    "page": printed_page,
                    "text": text,
                    "language": language,
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                total_written += 1

    print(f"[DONE] Extracted {total_written} textbook pages into {config.PAGES_JSONL}")


if __name__ == "__main__":
    process_books()
