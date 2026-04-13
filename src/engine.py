import fitz  # PyMuPDF
import os

# --- [1. 경로 및 오픈소스 폰트 설정] ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(BASE_DIR, "assets", "fonts")

# 프로젝트 내장 폰트 매핑 (OFL 라이선스 준수)
FONT_MAP = {
    "Regular": os.path.join(FONT_DIR, "NotoSansKR-Regular.ttf"),
    "Bold": os.path.join(FONT_DIR, "NotoSansKR-Bold.ttf"),
    "Gulim": os.path.join(FONT_DIR, "Gulim.ttf"),
    "Dotum": os.path.join(FONT_DIR, "Dotum.ttf"),
    "Batang": os.path.join(FONT_DIR, "Batang.ttf"),
    "Gungsuh": os.path.join(FONT_DIR, "Gungsuh.ttf")
}

# 폰트 부재 시 시스템 기본 폰트로 대체
FALLBACK_REGULAR = FONT_MAP["Regular"] if os.path.exists(FONT_MAP["Regular"]) else "helv"

def find_local_font_path(pdf_font_name):
    """PDF 원본 폰트명 기반 로컬 폰트 매칭"""
    name_lower = pdf_font_name.lower()
    if "gulim" in name_lower and os.path.exists(FONT_MAP["Gulim"]): return FONT_MAP["Gulim"]
    if "dotum" in name_lower and os.path.exists(FONT_MAP["Dotum"]): return FONT_MAP["Dotum"]
    if "batang" in name_lower and os.path.exists(FONT_MAP["Batang"]): return FONT_MAP["Batang"]
    if "gungsuh" in name_lower and os.path.exists(FONT_MAP["Gungsuh"]): return FONT_MAP["Gungsuh"]
    if "bold" in name_lower and os.path.exists(FONT_MAP["Bold"]): return FONT_MAP["Bold"]
    return FONT_MAP["Regular"] if os.path.exists(FONT_MAP["Regular"]) else FALLBACK_REGULAR

def get_original_style(page, target_text):
    """텍스트 속성(크기, 색상, 두께 플래그 및 물리적 비율) 정밀 분석"""
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                line_text = "".join([s["text"] for s in line["spans"]])
                
                # 검색 대상 텍스트 포함 여부 확인
                if target_text.strip() in line_text or line_text.strip() in target_text.strip():
                    # 데이터 파편 방지를 위한 라인 내 최장 텍스트 덩어리 선정
                    longest_span = max(line["spans"], key=lambda s: len(s["text"]))
                    font_name = longest_span["font"].lower()
                    
                    # 볼드 판정 1: 시스템 플래그 및 폰트 키워드 검사
                    is_bold_flag = bool(longest_span["flags"] & 18)
                    has_bold_keyword = any(k in font_name for k in ["bold", "bd", "heavy", "black", "demi"])
                    
                    # 볼드 판정 2: 물리적 글자 너비 비율 계산 (황금 비율 0.52 적용)
                    char_count = len(longest_span["text"].strip())
                    width_ratio = (longest_span["bbox"][2] - longest_span["bbox"][0]) / char_count / longest_span["size"] if char_count > 0 else 0
                        
                    is_bold_logic = is_bold_flag or has_bold_keyword or width_ratio > 0.52
                    
                    # 색상 데이터 추출 (RGB 변환)
                    c = longest_span["color"]
                    rgb = (((c >> 16) & 255)/255, ((c >> 8) & 255)/255, (c & 255)/255)
                    return longest_span["size"], rgb, longest_span["font"], is_bold_logic
                    
    return 11, (0, 0, 0), "Unknown", False


# --- [2. 핵심 기능 함수] ---

def mask_text(input_path, output_path, target_text):
    """핵심 기능 1: 텍스트 탐지 및 화이트아웃 마스킹 (테스트 및 비식별화용)"""
    print(f"\n[기능 1] 마스킹 처리: '{target_text}'")
    doc = fitz.open(input_path)
    page = doc[0]
    
    # 대상 텍스트 좌표 검색 및 마스킹 영역 설정
    instances = page.search_for(target_text)
    if instances:
        for inst in instances:
            page.add_redact_annot(inst, fill=(0, 0, 0)) # 검은색으로 마스킹
        page.apply_redactions() # 물리적 삭제 적용
    
    doc.save(output_path, clean=True)
    doc.close()
    print(f"✅ 처리 완료: {output_path}")


def translate_text_smart(input_path, output_path, translation_map):
    """핵심 기능 2: 레이아웃 및 스타일 복제형 번역 엔진 (1:1 스타일 이식)"""
    print(f"\n🚀 [기능 2] 스마트 번역 엔진: 레이아웃 보존 및 스타일 복제 중...")
    doc = fitz.open(input_path)
    page = doc[0]
    pending_actions = []
    handled_rects = [] 

    # 처리 우선순위 설정을 위한 문자열 길이 기준 정렬
    sorted_map = dict(sorted(translation_map.items(), key=lambda x: len(x[0]), reverse=True))

    for old_txt, new_txt in sorted_map.items():
        search_key = old_txt.strip()
        if not search_key or search_key == new_txt.strip():
            continue

        instances = page.search_for(search_key)
        if not instances: continue

        # 원본 스타일 데이터 추출 및 매칭 폰트 로드
        orig_size, orig_color, orig_font_name, is_bold_orig = get_original_style(page, search_key)
        matched_font_file = find_local_font_path(orig_font_name)
        
        for inst in instances:
            # 중복 수술 및 영역 겹침 방지 (교차 영역 50% 기준)
            if any(r.intersect(inst).get_area() > inst.get_area() * 0.5 for r in handled_rects):
                continue

            # 기존 텍스트 삭제 영역 지정
            page.add_redact_annot(inst, fill=(1, 1, 1))
            handled_rects.append(inst)
            
            # 번역 텍스트 삽입 대기열 추가 (스타일 속성 계승)
            pending_actions.append({
                "point": fitz.Point(inst.x0, inst.y1 - 2), 
                "text": new_txt.strip(), 
                "size": orig_size, 
                "color": orig_color, 
                "font_file": matched_font_file, 
                "is_bold": is_bold_orig
            })

    # 전체 마스킹 일괄 적용 및 신규 텍스트 렌더링
    page.apply_redactions()
    
    for act in pending_actions:
        page.insert_text(
            act["point"], act["text"], 
            fontname="ko", fontfile=act["font_file"], 
            fontsize=act["size"], color=act["color"], 
            render_mode=2 if act["is_bold"] else 0, # 볼드 여부에 따른 렌더링 모드 설정
            border_width=0.02 if act["is_bold"] else 0
        )

    doc.save(output_path, clean=True)
    doc.close()
    print(f"\n✨ 완벽 수술 완료: {output_path}")