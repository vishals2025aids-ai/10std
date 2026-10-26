import os
import re
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

import config

load_dotenv()

try:
    from google import genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


def translate_to_tamil(text: str) -> str:
    """
    Translates text into Tamil using a robust fallback translator.
    Preserves formatting and gracefully returns original text if network is offline.
    """
    if not text or not text.strip():
        return text
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ta&dt=t&q=" + urllib.parse.quote(text)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=6) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            translated = "".join([part[0] for part in data[0] if part and len(part) > 0 and part[0]])
            return translated if translated.strip() else text
    except Exception as exc:
        print(f"[WARN] Translation to Tamil fallback failed ({exc}) -> using raw text.")
        return text


def fallback_summary(page_text: str, lang: str = "en") -> str:
    """
    Plain bullet summary extracted directly from the textbook page text.
    When lang == 'ta', the summary and bullet points are translated into Tamil (தமிழ்).
    """
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", page_text)
        if len(s.strip()) > 25
    ]
    if not sentences:
        sentences = [line.strip() for line in page_text.splitlines() if line.strip()]

    intro = " ".join(sentences[:2]) if sentences else page_text[:300]
    bullets = sentences[2:] if len(sentences) > 2 else sentences[:3]

    if lang == "ta":
        header = "### 📖 [பாடநூல் நேரடி விளக்கம் - சரிபார்க்கப்பட்ட தமிழ்நாடு பாடத்திட்டம்]"
        has_tamil = any(0x0B80 <= ord(ch) <= 0x0BFF for ch in page_text)
        intro_ta = intro if has_tamil else translate_to_tamil(intro)
        bullet_ta_list = []
        for b in bullets:
            bullet_ta_list.append(b if has_tamil else translate_to_tamil(b))
        bullet_lines = "\n".join(f"• {b}" for b in bullet_ta_list)
        sec_ov = "### 📌 பாடக் கண்ணோட்டம் (Topic Overview)"
        sec_kc = "### 🔍 முக்கியக் கருத்துக்கள் & ஆழ்ந்த விளக்கம் (Key Concepts & In-Depth Breakdown)"
        return f"{header}\n\n{sec_ov}\n{intro_ta}\n\n{sec_kc}\n{bullet_lines}"

    header = "### 📖 [Offline Textbook Explanation - Verified Curriculum Syllabus]"
    bullet_lines = "\n".join(f"• {b}" for b in bullets)
    sec_ov = "### 📌 Topic Overview"
    sec_kc = "### 🔍 Key Concepts & In-Depth Breakdown"
    return f"{header}\n\n{sec_ov}\n{intro}\n\n{sec_kc}\n{bullet_lines}"


def build_prompt(page_record: dict, lang: str = "en", user_query: str = "") -> str:
    """Build a strict grounding prompt for a 15-year-old (10th standard) student."""
    if lang == "ta":
        lang_instruction = (
            "முக்கிய விதி: முழுமையான விளக்கத்தையும் எளிய, இயல்பான மற்றும் தெளிவான தமிழில் (Tamil) மட்டுமே எழுத வேண்டும்! "
            "தொடக்க சுருக்கம் மற்றும் 3 முக்கிய குறிப்புகள் அனைத்தும் தமிழிலேயே இருக்க வேண்டும். "
            "தேவைப்பட்டால் கடினமான அறிவியல்/கணித கலைச்சொற்களை அடைப்புக்குறிக்குள் ஆங்கிலத்தில் (English) குறிப்பிடலாம்."
        )
    else:
        lang_instruction = "Write a comprehensive, deep, and engaging student-friendly explanation in clear English suitable for a 15-year-old (10th standard) student. Ground your answer strictly on the textbook page, detailing exact scientific mechanisms, mathematical proofs or formulas, historical causes and effects, or literary themes."

    return f"""You are PageMate, a friendly and highly knowledgeable 10th standard textbook tutor.
Explain ONLY the textbook page text provided below for a 10th standard student.

STRICT INSTRUCTIONS:
1. Use ONLY facts present in the TEXTBOOK PAGE below. Do NOT add outside facts or external internet knowledge.
2. Start with a simple 2-3 sentence overview explaining the core idea clearly.
3. Provide a structured, in-depth breakdown with sections for Overview, Key Concepts, Formulas/Laws/Mechanisms, and Student Exam Takeaways.
4. {lang_instruction}

Subject: {page_record['subject'].title()} | Chapter: {page_record['chapter']} | Page: {page_record['page']}
Student Query: {user_query}

TEXTBOOK PAGE:
----------------------------------------
{page_record['text']}
----------------------------------------
"""


def explain_page(page_record: dict, lang: str = "en", user_query: str = "") -> dict:
    """
    Return the explanation and metadata for a single retrieved page.
    Automatically respects lang ('en' or 'ta').
    Falls back to fallback_summary() if no API key or if Gemini call fails.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        api_key = getattr(config, "GEMINI_API_KEY", "").strip()

    if not api_key or not HAS_GENAI:
        return {
            "explanation": fallback_summary(page_record.get("text_ta", "") if (lang == "ta" and page_record.get("text_ta")) else page_record.get("text", ""), lang=lang),
            "used_fallback": True,
        }

    try:
        client = genai.Client(api_key=api_key)
        prompt = build_prompt(page_record, lang=lang, user_query=user_query)
        response = client.models.generate_content(
            model=getattr(config, "GEMINI_MODEL_NAME", "gemini-2.5-flash"),
            contents=prompt,
        )
        answer = (response.text or "").strip()
        if not answer:
            raise ValueError("Empty response from Gemini")
        return {
            "explanation": answer,
            "used_fallback": False,
        }
    except Exception as exc:
        print(f"[WARN] Gemini call failed ({exc}) -> using fallback summary (lang={lang}).")
        return {
            "explanation": fallback_summary(page_record.get("text_ta", "") if (lang == "ta" and page_record.get("text_ta")) else page_record.get("text", ""), lang=lang),
            "used_fallback": True,
        }


def tutor_chat(message: str, history: list = None, lang: str = "en", subject: str = None) -> dict:
    """
    Interactive Gemini AI Tutor conversational assistant.
    Provides curriculum-grounded step-by-step guidance for 10th standard students in English or Tamil.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        api_key = getattr(config, "GEMINI_API_KEY", "").strip()

    history = history or []
    subj_hint = f"for {subject.upper()}" if subject else "covering 10th Standard Science, Maths, Social Science, English, and Tamil"

    if lang == "ta":
        lang_instruction = (
            "முக்கிய விதி: மாணவருக்கு எளிய, தெளிவான மற்றும் அன்பான தமிழில் (Tamil) மட்டுமே பதிலளிக்க வேண்டும்! "
            "பாடக்கருத்துக்களை படிபடியாகப் புரிய வைக்கவும். கடினமான அறிவியல் சொற்களை ஆங்கிலத்தில் அடைப்புக்குறிக்குள் கொடுக்கலாம்."
        )
    else:
        lang_instruction = "Respond in simple, friendly, encouraging English suitable for a 10th standard student."

    if not api_key or not HAS_GENAI:
        if lang == "ta":
            offline_msg = (
                f"வணக்கம்! நான் உங்கள் பேஜ்மேட் (PageMate) AI ஆசிரியர் ({subj_hint}).\n\n"
                "10ஆம் வகுப்பு பாடப்புத்தகக் கருத்துக்கள், சூத்திரங்கள், அறிவியல் விதிகளுக்கு படிபடியான விளக்கங்களை நான் உங்களுக்கு வழங்குகிறேன்.\n\n"
                "(குறிப்பு: தற்போது ஆஃப்லைன் முறையில் செயல்படுகிறது. ஜெமினி 2.5 ஃப்ளாஷ் நேரடி AI உரையாடலை இயக்க `.env` கோப்பில் உங்கள் GEMINI_API_KEY-ஐ அமைக்கவும். "
                "ஸ்மார்ட் தேடல் மற்றும் பாடநூல் காட்சிப் பலகையில் சரிபார்க்கப்பட்ட புத்தகப் பக்கங்களை நீங்கள் எப்போது வேண்டுமானாலும் பார்வையிடலாம்!)"
            )
        else:
            offline_msg = (
                f"Hello! I am PageMate AI Tutor ({subj_hint}).\n\n"
                "I am here to help you master 10th standard concepts step-by-step, review formulas, understand lessons, and clarify questions.\n\n"
                "(Note: Operating in local offline mode. Add your GEMINI_API_KEY in .env to activate live generative dialogue with Gemini 2.5 Flash. You can also explore exact pages and verified summaries using the Smart Search and Textbook Source Viewer tabs!)"
            )
        return {
            "reply": offline_msg,
            "used_fallback": True,
        }

    try:
        client = genai.Client(api_key=api_key)
        system_instruction = (
            f"You are PageMate AI Tutor, an empathetic, encouraging 10th standard textbook teacher {subj_hint}.\n"
            f"{lang_instruction}\n"
            "Rules:\n"
            "1. Explain step-by-step with simple real-world analogies and clear headings.\n"
            "2. When relevant, reference Tamil Nadu State Board 10th standard curriculum concepts or key textbook pages.\n"
            "3. Keep explanations structured, easy to remember, and focused on exam confidence.\n"
            "4. Conclude with a warm encouraging note or a quick self-test question for the student."
        )

        conv_lines = []
        for turn in history[-6:]:
            role = turn.get("role", "user")
            txt = turn.get("text", "")
            conv_lines.append(f"{role.capitalize()}: {txt}")
        conv_lines.append(f"Student: {message}")
        conv_lines.append("Tutor:")

        prompt = f"{system_instruction}\n\n" + "\n".join(conv_lines)
        response = client.models.generate_content(
            model=getattr(config, "GEMINI_MODEL_NAME", "gemini-2.5-flash"),
            contents=prompt,
        )
        reply = (response.text or "").strip()
        if not reply:
            raise ValueError("Empty response from Gemini")
        return {"reply": reply, "used_fallback": False}
    except Exception as exc:
        print(f"[WARN] Gemini tutor chat failed ({exc}) -> using offline helper reply.")
        if lang == "ta":
            err_msg = f"தற்போது ஜெமினி சேவையை இணைக்க முடியவில்லை ({exc}). ஸ்மார்ட் தேடல் பகுதியில் நேரடி பாடநூல் விளக்கங்களை நீங்கள் தமிழில் காணலாம்!"
        else:
            err_msg = f"I am currently operating in offline mode ({exc}). You can browse verified textbook text in the Smart Search & RAG Explorer tab!"
        return {
            "reply": err_msg,
            "used_fallback": True,
        }
