import fitz
import os
import re
from .ai_bridge import bridge

# --- [1. 공통 설정 및 유틸리티] ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

FONT_MAP = {
    "Noto": os.path.join(FONTS_DIR, "NotoSansKR-Regular.ttf"),
    "Gulim": os.path.join(FONTS_DIR, "Gulim.ttf"),
    "Dotum": os.path.join(FONTS_DIR, "Dotum.ttf"),
    "Batang": os.path.join(FONTS_DIR, "Batang.ttf"),
    "Gungsuh": os.path.join(FONTS_DIR, "Gungsuh.ttf"),
}
FALLBACK_FONT = os.path.join(FONTS_DIR, "NotoSansKR-Regular.ttf")
PROTECT_SYMBOLS = [":", ",", ".", ";", ")", "-", " "]
LETTER_SPACING = 0.3

def has_korean(text):
    return bool(re.search(r'[\uac00-\ud7a3]', text))

def find_local_font_path(pdf_font_name):
    name_lower = pdf_font_name.lower()
    for key_name, file_path in FONT_MAP.items():
        if key_name.lower() in name_lower:
            return file_path
    return FALLBACK_FONT

def insert_text_with_spacing(page, point, text, fontname, fontfile, fontsize, color):
    current_x, current_y = point.x, point.y
    try:
        if fontfile and os.path.exists(fontfile):
            page.insert_font(fontname=fontname, fontfile=fontfile)
            font = fitz.Font(fontfile=fontfile)
        else:
            font = fitz.Font("cjk")
            fontname = "cjk"
    except Exception as e:
        print(f"⚠️ [Font Error] {e}")
        font = fitz.Font("cjk")
        fontname = "cjk"
    
    for char in text:
        page.insert_text(fitz.Point(current_x, current_y), char, 
                         fontname=fontname, fontsize=fontsize, color=color)
        current_x += font.text_length(char, fontsize=fontsize) + LETTER_SPACING

def extract_english_spans(doc):
    english_texts = set()
    for page in doc:
        for block in page.get_text("dict").get("blocks", []):
            if "lines" not in block: continue
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if not text: continue
                    if has_korean(text) and not re.search(r'[a-zA-Z]', text): continue
                    if re.search(r'[a-zA-Z]', text):
                        english_texts.add(text)
    return list(english_texts)

# --- [2. 주요 기능 함수] ---

def create_masked_pdf(pdf_bytes, target_text="Apple", color=(0, 0, 0)):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    targets = [text.strip() for text in target_text.split(",") if text.strip()]
    
    for page in doc:
        for target in targets:
            for inst in page.search_for(target):
                page.draw_rect(inst, color=color, fill=color)
                
    res = doc.write()
    doc.close()
    return res

def translate_text_manual(pdf_bytes, translation_map):
    return _core_translation_engine(pdf_bytes, translation_map, mode="manual")

def translate_text_smart(pdf_bytes):
    print("🚀 [Engine] 지능형 번역 시작")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    english_texts = extract_english_spans(doc)
    print(f"📄 [Engine] 영어 span 추출 완료: {english_texts}")
    
    ai_map = bridge.get_translation_map(english_texts)
    
    print(f"🛠 [Engine] 변환 엔진 가동 (단어수: {len(ai_map)})")
    return _core_translation_engine(pdf_bytes, ai_map, mode="smart")

# --- [3. 통합 번역 코어 엔진] ---

def _core_translation_engine(pdf_bytes, translation_map, mode="smart"):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    
    for page in doc:
        pending_actions = []
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block: continue
            for line in block["lines"]:
                for span in line["spans"]:
                    raw_text = span["text"]
                    if not raw_text.strip(): continue
                    if has_korean(raw_text) and not re.search(r'[a-zA-Z]', raw_text): continue

                    final_text = None
                    if mode == "smart":
                        clean_raw = raw_text.strip()
                        if clean_raw in translation_map:
                            final_text = translation_map[clean_raw]
                        else:
                            core_text, suffix = clean_raw, ""
                            for sym in PROTECT_SYMBOLS:
                                if core_text.endswith(sym):
                                    suffix = sym + suffix
                                    core_text = core_text[:-len(sym)]
                            if core_text in translation_map:
                                final_text = translation_map[core_text] + suffix
                            else:
                                final_text = clean_raw
                                matched = False
                                for k, v in translation_map.items():
                                    if k in final_text:
                                        final_text = final_text.replace(k, v)
                                        matched = True
                                if not matched:
                                    final_text = None
                    else:
                        matched_keys = [k for k in translation_map.keys() if k in raw_text]
                        if matched_keys:
                            final_text = raw_text
                            for k in matched_keys:
                                final_text = final_text.replace(k, translation_map[k])

                    if final_text:
                        orig_color = (((span["color"] >> 16) & 255) / 255, 
                                      ((span["color"] >> 8) & 255) / 255, 
                                      (span["color"] & 255) / 255)
                        page.add_redact_annot(span["bbox"], fill=(1, 1, 1))
                        pending_actions.append({
                            "point": fitz.Point(span["origin"]), "text": final_text,
                            "size": span["size"], "color": orig_color,
                            "font_file": find_local_font_path(span["font"]),
                            "font_name": f"f_ko_{len(pending_actions)}"
                        })

        page.apply_redactions()
        for act in pending_actions:
            insert_text_with_spacing(page, act["point"], act["text"], act["font_name"], 
                                     act["font_file"], act["size"], act["color"])

    res = doc.write()
    doc.close()
    return res