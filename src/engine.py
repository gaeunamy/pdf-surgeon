import fitz
import os

# --- [1. 공통 설정 및 유틸리티] ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

# 폰트 및 기호 설정
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

def find_local_font_path(pdf_font_name):
    """PDF 내의 폰트 이름을 기반으로 로컬 폰트 파일을 찾음"""
    name_lower = pdf_font_name.lower()
    for key_name, file_path in FONT_MAP.items():
        if key_name.lower() in name_lower:
            return file_path
    return FALLBACK_FONT

def insert_text_with_spacing(page, point, text, fontname, fontfile, fontsize, color):
    """자간을 유지하며 텍스트를 삽입하는 함수"""
    current_x, current_y = point.x, point.y
    try:
        font = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font("cjk")
    except:
        font = fitz.Font("cjk")
        fontfile, fontname = None, "cjk"
    
    for char in text:
        page.insert_text(fitz.Point(current_x, current_y), char, 
                         fontname=fontname, fontfile=fontfile, fontsize=fontsize, color=color)
        current_x += font.text_length(char, fontsize=fontsize) + LETTER_SPACING

# --- [2. 주요 기능 함수] ---

# 기능1: 텍스트 마스킹 (특정 텍스트를 색상 박스로 가림)
def mask_text(input_path, output_path, target_text, color=(0, 0, 0)):
    doc = fitz.open(input_path)
    for page in doc:
        for inst in page.search_for(target_text):
            page.draw_rect(inst, color=color, fill=color)
    doc.save(output_path)
    doc.close()
    print(f"\n{'-'*50}\n🛡️ [작업 완료] 텍스트 마스킹 (타겟: {target_text})\n📁 저장 경로: {output_path}\n{'-'*50}")

# 기능 2: 수동 교체 (부분 일치 지원)
def translate_text_manual(input_path, output_path, translation_map):
    _core_translation_engine(input_path, output_path, translation_map, mode="manual")
    print(f"\n{'-'*50}\n🛠️ [작업 완료] 수동 부분 교체\n📁 저장 경로: {output_path}\n{'-'*50}")

# 기능3: 지능형 번역 (AI - 정밀 매칭 및 기호 보호)"""
def translate_text_smart(input_path, output_path, translation_map):
    _core_translation_engine(input_path, output_path, translation_map, mode="smart")

# --- [3. 통합 번역 코어 엔진] ---

def _core_translation_engine(input_path, output_path, translation_map, mode="smart"):
    """smart와 manual의 공통 로직을 처리하는 핵심 엔진"""
    doc = fitz.open(input_path)
    
    for page in doc:
        pending_actions = []
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if "lines" not in block: continue
            for line in block["lines"]:
                for span in line["spans"]:
                    raw_text = span["text"]
                    if not raw_text.strip(): continue

                    final_text = None

                    if mode == "smart": # 지능형 모드
                        # 1순위: 전체 문장 그대로 매칭 시도 (AI 응답과 1:1 매칭)
                        clean_raw = raw_text.strip()
                        if clean_raw in translation_map:
                            final_text = translation_map[clean_raw]
                        else:
                            # 2순위: 실패 시 기호 분리 후 매칭 시도 (기존 로직)
                            core_text, suffix = clean_raw, ""
                            for sym in PROTECT_SYMBOLS:
                                if core_text.endswith(sym):
                                    suffix = sym + suffix
                                    core_text = core_text[:-len(sym)]
                            
                            if core_text in translation_map:
                                final_text = translation_map[core_text] + suffix

                    else: # 수동 모드
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

    doc.save(output_path, clean=True)
    doc.close()