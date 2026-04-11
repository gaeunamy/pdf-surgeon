import fitz  # PyMuPDF
import os

# --- [1. 공통 설정 및 유틸리티] ---
FONT_MAP = {
    "Malgun": "C:/Windows/Fonts/malgun.ttf",
    "Gulim": "C:/Windows/Fonts/gulim.ttc",
    "Dotum": "C:/Windows/Fonts/gulim.ttc",
    "Batang": "C:/Windows/Fonts/batang.ttc",
    "Gungsuh": "C:/Windows/Fonts/gungsuh.ttc",
}
FALLBACK_REGULAR = "C:/Windows/Fonts/malgun.ttf"

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
                        is_bold_flag = bool(span["flags"] & 2)
                        char_count = len(span["text"]) if len(span["text"]) > 0 else 1
                        avg_char_width = (span["bbox"][2] - span["bbox"][0]) / char_count
                        width_ratio = avg_char_width / span["size"]
                        is_bold_logic = is_bold_flag or "bold" in font_name.lower() or width_ratio > 0.5
                        c = span["color"]
                        rgb = (((c >> 16) & 255)/255, ((c >> 8) & 255)/255, (c & 255)/255)
                        return span["size"], rgb, span["font"], is_bold_logic, width_ratio
    return 11, (0, 0, 0), "Unknown", False, 0.0

def get_line_bbox(dict_data, target_text):
    for block in dict_data["blocks"]:
        if "lines" in block:
            for line in block["lines"]:
                line_text = "".join([s["text"] for s in line["spans"]])
                if target_text in line_text:
                    return fitz.Rect(line["bbox"]), line_text
    return None, None

# --- [2. 주요 기능 함수] ---

def mask_text(input_path, output_path, target_text, color=(0, 0, 0)):
    """기능 1: 텍스트 마스킹"""
    doc = fitz.open(input_path)
    for page in doc:
        instances = page.search_for(target_text)
        for inst in instances:
            page.add_redact_annot(inst, fill=color)
        page.apply_redactions()
    doc.save(output_path)
    doc.close()
    print(f"✅ [MASK] '{target_text}' 처리 완료")

def translate_text_smart(input_path, output_path, translation_map):
    """기능 2: 지능형 레이아웃 번역 (상세 로그 버전)"""
    print(f"\n🚀 [Smart Engine] 자연스러운 레이아웃 모드 가동")
    doc = fitz.open(input_path)
    page = doc[0]
    dict_data = page.get_text("dict")
    pending_actions = []

    for old_txt, new_txt in translation_map.items():
        instances = page.search_for(old_txt)
        if not instances: continue

        orig_size, orig_color, orig_font_name, is_bold_orig, width_ratio = get_original_style(page, old_txt)
        matched_font_file = find_local_font_path(orig_font_name)
        
        for inst in instances:
            old_w = inst.width
            new_w = get_text_width(new_txt, orig_size, matched_font_file)
            is_length_changed = abs(new_w - old_w) > 2
            line_rect, full_line = get_line_bbox(dict_data, old_txt)

            if is_length_changed and line_rect:
                # 🟧 줄 재구성 로그 출력
                reconstructed_line = full_line.replace(old_txt, new_txt)
                print(f"🟧 [LINE RECONSTRUCT] '{full_line.strip()}' ➔ '{reconstructed_line.strip()}'")
                print(f"    └ 폰트={orig_font_name}, 볼드판정={is_bold_orig},비율={width_ratio:.2f}")
                
                parts = full_line.split(old_txt, 1)
                prefix, suffix = parts[0], parts[1] if len(parts) > 1 else ""
                current_x = line_rect.x0

                if prefix:
                    pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": prefix, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": False})
                    current_x += get_text_width(prefix, orig_size, matched_font_file)

                pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": new_txt, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": True})
                current_x += get_text_width(new_txt, orig_size, matched_font_file)

                if suffix:
                    pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": suffix, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": False})
                page.add_redact_annot(line_rect, fill=(1, 1, 1))
            else:
                # 🟦 단순 단어 교체 로그 출력
                print(f"🟦 [WORD REPLACE] '{old_txt}' ➔ '{new_txt}'")
                print(f"    └ 폰트={orig_font_name}, 볼드={is_bold_orig}, 비율={width_ratio:.2f}")
                page.add_redact_annot(inst, fill=(1, 1, 1))
                pending_actions.append({"point": fitz.Point(inst.x0, inst.y1 - 2), "text": new_txt, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": True})

    page.apply_redactions()
    for act in pending_actions:
        page.insert_text(
            act["point"], act["text"], 
            fontname="ko", fontfile=act["font_file"], 
            fontsize=act["size"], color=act["color"], 
            render_mode=2 if act["is_bold"] else 0, 
            border_width=0.02 if act["is_bold"] else 0
        )

    doc.save(output_path, clean=True)
    doc.close()
    print(f"\n✨ 지능형 번역 완료: {output_path}")