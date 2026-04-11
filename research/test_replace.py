import fitz
import os

# 🗺️ 폰트 매핑 사전 (내 PC에 있는 폰트들을 등록)
# PDF에서 읽어온 폰트 이름의 '일부'만 맞아도 해당 폰트 파일을 연결
FONT_MAP = {
    "Malgun": "C:/Windows/Fonts/malgun.ttf",       # 맑은 고딕
    "Gulim": "C:/Windows/Fonts/gulim.ttc",         # 굴림
    "Batang": "C:/Windows/Fonts/batang.ttc",       # 바탕
    "Gungsuh": "C:/Windows/Fonts/gungsuh.ttc",     # 궁서
    "Dotum": "C:/Windows/Fonts/dotum.ttc",         # 돋움
}

# 기본 폰트 (매핑 사전에 없는 폰트일 경우)
FALLBACK_FONT = "C:/Windows/Fonts/malgun.ttf"

def get_original_style(page, target_text):
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    if target_text in span["text"]:
                        original_size = span["size"]
                        color_int = span["color"]
                        r = ((color_int >> 16) & 255) / 255
                        g = ((color_int >> 8) & 255) / 255
                        b = (color_int & 255) / 255
                        
                        original_font = span["font"] # 폰트 이름표
                        return original_size, (r, g, b), original_font
                        
    return 11, (0, 0, 0), "Unknown"

# 폰트 이름표를 보고 내 PC의 진짜 폰트 파일을 찾아주는 함수
def find_local_font_path(pdf_font_name):
    # 대소문자 구분 없이 비교하기 위해 소문자로 변환
    pdf_font_name_lower = pdf_font_name.lower()
    
    for key_name, file_path in FONT_MAP.items():
        if key_name.lower() in pdf_font_name_lower:
            if os.path.exists(file_path):
                return file_path
                
    # 못 찾으면 기본 폰트 반환
    return FALLBACK_FONT

def replace_text_in_pdf(input_path, output_path, old_text, new_text):
    print(f"📄 '{old_text}'를 지우고 '{new_text}'(으)로 덮어쓰기를 시작합니다...")
    
    doc = fitz.open(input_path)
    page = doc[0]
    
    # 1. 스타일과 폰트 이름 읽어오기
    orig_size, orig_color, orig_font_name = get_original_style(page, old_text)
    
    # 2. 내 PC에서 똑같은(또는 비슷한) 폰트 파일 경로 찾기
    matched_font_path = find_local_font_path(orig_font_name)
    
    # print(f"🔍 [스타일 탐지] 원래 폰트: {orig_font_name}")
    # print(f"🎯 [폰트 매칭] 적용할 폰트 파일: {matched_font_path}")
    # print(f"📏 [크기/색상] 크기: {orig_size:.1f}, 색상: {orig_color}")

    text_instances = page.search_for(old_text)
    if not text_instances:
        print(f"⚠️ 문서에서 '{old_text}'를 찾을 수 없습니다.")
        return
        
    for inst in text_instances:
        page.add_redact_annot(inst, fill=(1, 1, 1)) 
        page.apply_redactions()
        
        point = fitz.Point(inst.x0, inst.y1 - 2) 
        
        # 3. 매칭된 폰트 파일을 넣어서 글자 쓰기
        page.insert_text(
            point, 
            new_text, 
            fontname="custom_font",
            fontfile=matched_font_path, # 찾아낸 폰트 파일 경로 적용
            fontsize=orig_size,   
            color=orig_color      
        )
        
    doc.save(output_path)
    doc.close()
    print(f"\n✨ 작업 완료: {output_path}")

if __name__ == "__main__":
    INPUT_FILE = "sample.pdf"
    OUTPUT_FILE = "replaced_sample.pdf"
    
    OLD_TEXT = "홍길동 (Hong Gil-dong)"
    NEW_TEXT = "김철수 (Kim Chul Soo)"

    replace_text_in_pdf(INPUT_FILE, OUTPUT_FILE, OLD_TEXT, NEW_TEXT)