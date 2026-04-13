import fitz  # PyMuPDF
import os
import re

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
    name_lower = pdf_font_name.lower()
    for key_name, file_path in FONT_MAP.items():
        if key_name.lower() in name_lower:
            return file_path
    return FALLBACK_REGULAR

def get_text_width(text, size, font_path):
    font = fitz.Font(fontfile=font_path)
    return font.text_length(text, fontsize=size)

def get_original_style(page, target_text):
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    if target_text in span["text"]:
                        font_name = span["font"]
                        c = span["color"]
                        rgb = (((c >> 16) & 255)/255, ((c >> 8) & 255)/255, (c & 255)/255)
                        # 볼드체 감지 로직(is_bold_flag, width_ratio 등) 제거
                        return span["size"], rgb, font_name
    return 11, (0, 0, 0), "Unknown"

def get_line_bbox(dict_data, target_text):
    for block in dict_data["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                line_text = "".join([s["text"] for s in line["spans"]])
                if target_text in line_text:
                    return fitz.Rect(line["bbox"]), line_text
    return None, None

# --- [2. 주요 기능 함수] ---

def translate_text_smart(input_path, output_path, translation_map):
    """기능 2: 지능형 레이아웃 번역 (범용 기호 보호 및 의도 파악 적용, 볼드체 처리 제거)"""
    print(f"\n🚀 [Smart Engine] 범용 기호 보호 및 의도 파악 시스템 가동...")
    doc = fitz.open(input_path)
    page = doc[0]
    dict_data = page.get_text("dict")
    pending_actions = []

    # 보호할 기호 리스트
    PROTECT_SYMBOLS = [":", ",", ".", "-", ";", "/", "]", ")"]

    for old_txt, new_txt in translation_map.items():
        original_has_symbol = any(old_txt.endswith(s) for s in PROTECT_SYMBOLS)
        new_has_symbol = any(new_txt.endswith(s) for s in PROTECT_SYMBOLS)
        
        is_intentional_deletion = original_has_symbol and not new_has_symbol

        search_key = old_txt.rstrip(": ,.-[];/)]") 
        instances = page.search_for(search_key)
        if not instances: continue

        # 볼드체 관련 변수 반환받지 않음
        orig_size, orig_color, orig_font_name = get_original_style(page, search_key)
        matched_font_file = find_local_font_path(orig_font_name)
        
        for inst in instances:
            search_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 10, inst.y1)
            nearby_items = page.get_text("words", clip=search_rect)
            
            protected_suffix = ""
            current_inst = inst
            for item in nearby_items:
                symbol = item[4].strip()
                if symbol in PROTECT_SYMBOLS:
                    protected_suffix = symbol
                    current_inst = fitz.Rect(inst.x0, inst.y0, item[2], inst.y1)
                    break
            
            line_rect, full_line = get_line_bbox(dict_data, search_key)
            
            if protected_suffix and new_txt.endswith(protected_suffix):
                final_replacement = new_txt
            else:
                final_replacement = new_txt if is_intentional_deletion else new_txt + protected_suffix

            if line_rect:
                parts = full_line.split(search_key, 1)
                prefix = parts[0]
                suffix = parts[1] if len(parts) > 1 else ""
                if not is_intentional_deletion and protected_suffix and suffix.startswith(protected_suffix):
                    suffix = suffix[len(protected_suffix):]

                print(f"🟧 [RECONSTRUCT] '{full_line.strip()}' ➔ '{prefix + final_replacement + suffix}'")
                
                current_x = line_rect.x0
                # pending_actions에서 "is_bold" 키 삭제
                if prefix:
                    pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": prefix, "size": orig_size, "color": orig_color, "font_file": matched_font_file})
                    current_x += get_text_width(prefix, orig_size, matched_font_file)
                
                pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": final_replacement, "size": orig_size, "color": orig_color, "font_file": matched_font_file})
                current_x += get_text_width(final_replacement, orig_size, matched_font_file)

                if suffix:
                    pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": suffix, "size": orig_size, "color": orig_color, "font_file": matched_font_file})
                
                page.add_redact_annot(line_rect, fill=(1, 1, 1))
            else:
                page.add_redact_annot(current_inst, fill=(1, 1, 1))
                pending_actions.append({"point": fitz.Point(inst.x0, inst.y1 - 2), "text": final_replacement, "size": orig_size, "color": orig_color, "font_file": matched_font_file})

    page.apply_redactions()
    for act in pending_actions:
        # render_mode와 border_width 옵션 제거 (기본값인 일반 굵기로 렌더링됨)
        page.insert_text(
            act["point"], act["text"], 
            fontname="ko", fontfile=act["font_file"], 
            fontsize=act["size"], color=act["color"]
        )

    doc.save(output_path, clean=True)
    doc.close()
    print(f"\n✨ 지능형 번역 완료!: {output_path}")