import os
import fitz
from src.ai_bridge import AIAnalyzer
from src.engine import translate_text_smart

def extract_all_text(pdf_path):
    """PDF에서 AI 분석을 위한 전체 텍스트를 추출합니다."""
    doc = fitz.open(pdf_path)
    full_text = ""
    for page in doc:
        full_text += page.get_text()
    doc.close()
    return full_text

def run_ai_surgeon(input_filename):
    # 1. 경로 설정
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_path, "data", "input", input_filename)
    output_path = os.path.join(base_path, "data", "output", f"ai_fixed_{input_filename}")

    # 2. 텍스트 추출 (AI에게 줄 재료 준비)
    print(f"📄 문서 읽는 중: {input_filename}")
    pdf_content = extract_all_text(input_path)

    # 3. AI 분석 (수술 계획서 작성)
    analyzer = AIAnalyzer()
    translation_map = analyzer.generate_translation_map(pdf_content)
    
    print("\n📋 AI가 생성한 번역 지도:")
    import json
    print(json.dumps(translation_map, indent=2, ensure_ascii=False))

    # 4. 엔진 가동 (실제 수술 진행)
    if translation_map:
        translate_text_smart(input_path, output_path, translation_map)
    else:
        print("⚠️ AI가 번역할 대상을 찾지 못했습니다.")

if __name__ == "__main__":
    # 테스트할 파일명을 입력하세요
    TARGET_FILE = "sample.pdf" 
    run_ai_surgeon(TARGET_FILE)