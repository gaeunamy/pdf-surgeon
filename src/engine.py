import fitz
import os

# --- [1. 공통 설정 및 유틸리티] ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(BASE_DIR, "assets", "fonts")

FONT_MAP = {
    "Noto": os.path.join(FONTS_DIR, "NotoSansKR-Regular.ttf"),
    "Gulim": os.path.join(FONTS_DIR, "Gulim.ttf"),
    "Dotum": os.path.join(FONTS_DIR, "Dotum.ttf"),
    "Batang": os.path.join(FONTS_DIR, "Batang.ttf"),
    "Gungsuh": os.path.join(FONTS_DIR, "Gungsuh.ttf"),
    "Malgun": os.path.join(FONTS_DIR, "NotoSansKR-Regular.ttf"),
}
FALLBACK_FONT = os.path.join(FONTS_DIR, "NotoSansKR-Regular.ttf")

def find_local_font_path(pdf_font_name):
    """PDF 내의 폰트 이름을 기반으로 로컬 폰트 파일을 찾음"""
    name_lower = pdf_font_name.lower()
    for key_name, file_path in FONT_MAP.items():
        if key_name.lower() in name_lower:
            return file_path
    return FALLBACK_FONT

LETTER_SPACING = 0.3

def insert_text_with_spacing(page, point, text, fontname, fontfile, fontsize, color):
    current_x, current_y = point.x, point.y
    
    try:
        font = fitz.Font(fontfile=fontfile) if fontfile else fitz.Font("cjk")
    except:
        font = fitz.Font("cjk")
        fontfile = None
        fontname = "cjk"
    
    for char in text:
        page.insert_text(
            fitz.Point(current_x, current_y), 
            char, 
            fontname=fontname, 
            fontfile=fontfile, 
            fontsize=fontsize, 
            color=color
        )
        char_width = font.text_length(char, fontsize=fontsize)
        current_x += char_width + LETTER_SPACING

# --- [2. 주요 기능 함수] ---

def mask_text(input_path, output_path, target_text, color=(0, 0, 0)):
    """기능 1: 텍스트 마스킹"""
    doc = fitz.open(input_path)
    
    for page in doc:
        instances = page.search_for(target_text)
        for inst in instances:
            page.draw_rect(inst, color=color, fill=color)
        
    doc.save(output_path)
    doc.close()
    print(f"\n{'-'*50}\n🛡️ [작업 완료] 텍스트 마스킹 (타겟: {target_text})\n📁 저장 경로: {output_path}\n{'-'*50}")

def translate_text_smart(input_path, output_path, translation_map):
    """PDF의 텍스트를 찾아 폰트 크기/글씨체/위치를 유지한 채 번역된 텍스트로 교체"""
    doc = fitz.open(input_path)
    
    for page in doc:
        pending_actions = []

        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if "lines" not in block:
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    original_text = span["text"].strip()
                    
                    if original_text in translation_map:
                        translated_text = translation_map[original_text]
                        
                        orig_size = span["size"] 
                        orig_origin = fitz.Point(span["origin"]) 
                        orig_bbox = fitz.Rect(span["bbox"]) 
                        
                        # 원본 폰트 이름과 로컬 파일과 매칭
                        orig_font_name = span["font"]
                        matched_font_file = find_local_font_path(orig_font_name)
                        
                        # 색상 변환
                        c = span["color"]
                        orig_color = ((c >> 16) & 255) / 255, ((c >> 8) & 255) / 255, (c & 255) / 255
                        
                        page.add_redact_annot(orig_bbox, fill=(1, 1, 1))
                        
                        pending_actions.append({
                            "point": orig_origin,
                            "text": translated_text,
                            "size": orig_size, 
                            "color": orig_color,
                            "font_file": matched_font_file, # 매칭된 폰트 파일 지정
                            # 폰트 충돌을 막기 위해 텍스트마다 고유한 fontname 부여
                            "font_name": f"f_ko_{len(pending_actions)}" 
                        })

        page.apply_redactions()
        
        for act in pending_actions:
            insert_text_with_spacing(
                page=page,
                point=act["point"],
                text=act["text"],
                fontname=act["font_name"], # 개별 고유 폰트 이름
                fontfile=act["font_file"], # 원본과 일치하는 폰트 파일
                fontsize=act["size"],
                color=act["color"]
            )

    doc.save(output_path, clean=True)
    doc.close()