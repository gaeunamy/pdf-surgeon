import os
import fitz
import json
from src.ai_bridge import AIAnalyzer
from src.engine import translate_text_smart

def extract_texts_for_translation(pdf_path):
    """PDF에서 번역이 필요한 텍스트 조각(Span)들을 추출"""
    doc = fitz.open(pdf_path)
    extracted_texts = set() # 중복 번역 요청을 막기 위해 Set 사용
    
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        # 알파벳이 포함되어 있고, 길이가 2 이상인 의미있는 텍스트만 추출
                        if len(text) > 1 and any(c.isalpha() for c in text):
                            extracted_texts.add(text)
    doc.close()
    return list(extracted_texts)

def run_translation_pipeline(input_filename):
    # 1. 입출력 경로 설정
    base_path = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_path, "data", "input", input_filename)
    output_path = os.path.join(base_path, "data", "output", f"translated_{input_filename}")

    if not os.path.exists(input_path):
        print(f"❌ 입력 파일을 찾을 수 없습니다: {input_path}")
        return

    # 2. PDF에서 텍스트 추출
    print(f"📄 1. PDF 분석 및 텍스트 추출 중: {input_filename}")
    texts_to_translate = extract_texts_for_translation(input_path)
    
    if not texts_to_translate:
        print("⚠️ 번역할 영문 텍스트를 찾지 못했습니다.")
        return

    # 3. AI 분석 (번역 지도 생성)
    print(f"\n🧠 2. AI 번역 엔진 가동...")
    analyzer = AIAnalyzer()
    
    translation_map = analyzer.generate_translation_map(texts_to_translate)
    
    print("\n📋 3. AI가 생성한 번역 지도:")
    print(json.dumps(translation_map, indent=2, ensure_ascii=False))

    # 4. 물리적 PDF 텍스트 교체
    if translation_map:
        print(f"\n⚙️  4. PDF 문서 원본 레이아웃 텍스트 교체 중...")
        translate_text_smart(input_path, output_path, translation_map)

        print(f"\n{'-'*50}")
        print(f"✨ [작업 완료] 지능형 번역")
        print(f"📁 저장 경로: {output_path}")
        print(f"{'-'*50}")
    else:
        print("\n⚠️ 적용할 번역 데이터가 없습니다.")

if __name__ == "__main__":
    # 테스트할 파일명 입력 (data/input/ 폴더 안에 있어야 함)
    TARGET_FILE = "invoice.pdf" 
    run_translation_pipeline(TARGET_FILE)