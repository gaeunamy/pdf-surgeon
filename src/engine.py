import fitz  # PyMuPDF
import os
import re

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

def translate_text_smart(input_path, output_path, translation_map):
    """기능 2: 지능형 레이아웃 번역 (범용 기호 보호 및 의도 파악 적용)"""
    print(f"\n🚀 [Smart Engine] 범용 기호 보호 및 의도 파악 시스템 가동...")
    doc = fitz.open(input_path)
    page = doc[0]
    dict_data = page.get_text("dict")
    pending_actions = []

    # 보호할 기호 리스트
    PROTECT_SYMBOLS = [":", ",", ".", "-", ";", "/", "]", ")"]

    for old_txt, new_txt in translation_map.items():
        # [의도 파악] 사용자가 원본에 있던 기호를 결과물에서 직접 삭제했는지 확인
        original_has_symbol = any(old_txt.endswith(s) for s in PROTECT_SYMBOLS)
        new_has_symbol = any(new_txt.endswith(s) for s in PROTECT_SYMBOLS)
        
        # 원본엔 기호가 있는데 결과물엔 없다면 '의도적 삭제'로 간주
        is_intentional_deletion = original_has_symbol and not new_has_symbol

        # 검색 최적화를 위해 우측 기호 및 공백 제거
        search_key = old_txt.rstrip(": ,.-[];/)]") 
        instances = page.search_for(search_key)
        if not instances: continue

        orig_size, orig_color, orig_font_name, is_bold_orig, width_ratio = get_original_style(page, search_key)
        matched_font_file = find_local_font_path(orig_font_name)
        
        for inst in instances:
            # 1. [Spatial Grouping] 단어 우측 10px 이내 범용 기호 탐색
            search_rect = fitz.Rect(inst.x1, inst.y0, inst.x1 + 10, inst.y1)
            nearby_items = page.get_text("words", clip=search_rect)
            
            protected_suffix = ""
            current_inst = inst
            for item in nearby_items:
                symbol = item[4].strip()
                if symbol in PROTECT_SYMBOLS:
                    protected_suffix = symbol
                    # 기호가 발견되면 지우기 영역을 해당 기호까지 확장
                    current_inst = fitz.Rect(inst.x0, inst.y0, item[2], inst.y1)
                    break
            
            # 2. 줄 재구성 및 교체 로직
            line_rect, full_line = get_line_bbox(dict_data, search_key)
            
            # 의도적으로 지운 게 아니라면 탐지된 기호를 다시 붙여줌
            if is_intentional_deletion:
                final_replacement = new_txt
            else:
                # 번역어(new_txt)가 이미 기호로 끝나고 있다면 suffix를 붙이지 않음
                if protected_suffix and new_txt.endswith(protected_suffix):
                    final_replacement = new_txt
                else:
                    final_replacement = new_txt + protected_suffix

            if line_rect:
                parts = full_line.split(search_key, 1)
                prefix = parts[0]
                # 이미 protected_suffix를 통해 기호를 처리하므로 원본 suffix에서 해당 기호 제거 시도
                suffix = parts[1] if len(parts) > 1 else ""
                if not is_intentional_deletion and protected_suffix and suffix.startswith(protected_suffix):
                    suffix = suffix[len(protected_suffix):]

                print(f"🟧 [RECONSTRUCT] '{full_line.strip()}' ➔ '{prefix + final_replacement + suffix}'")
                
                current_x = line_rect.x0
                if prefix:
                    pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": prefix, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": False})
                    current_x += get_text_width(prefix, orig_size, matched_font_file)
                
                pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": final_replacement, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": True})
                current_x += get_text_width(final_replacement, orig_size, matched_font_file)

                if suffix:
                    pending_actions.append({"point": fitz.Point(current_x, inst.y1 - 2), "text": suffix, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": False})
                
                page.add_redact_annot(line_rect, fill=(1, 1, 1))
            else:
                page.add_redact_annot(current_inst, fill=(1, 1, 1))
                pending_actions.append({"point": fitz.Point(inst.x0, inst.y1 - 2), "text": final_replacement, "size": orig_size, "color": orig_color, "font_file": matched_font_file, "is_bold": True})

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
    print(f"\n✨ 지능형 번역 완료!: {output_path}")