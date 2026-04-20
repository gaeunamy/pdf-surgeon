import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
import sys

# 프로젝트 루트 경로를 추가하여 src 모듈 인식
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ai_bridge import AIAnalyzer
from src.engine import translate_text_smart
from main import extract_texts_for_translation

app = FastAPI(title="PDF AI 번역기 API")

# 저장될 폴더 경로 설정
UPLOAD_DIR = "data/input"
OUTPUT_DIR = "data/output"

# 폴더가 없으면 생성
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.post("/translate/")
async def translate_pdf(file: UploadFile = File(...)):
    """PDF 파일을 받아 AI 지능형 번역을 수행하고 결과 파일을 반환합니다."""
    
    # 1. 업로드된 파일 저장
    input_path = os.path.join(UPLOAD_DIR, file.filename)
    output_filename = f"translated_{file.filename}"
    output_path = os.path.join(OUTPUT_DIR, output_filename)

    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # 2. 텍스트 추출
        texts_to_translate = extract_texts_for_translation(input_path)
        
        if not texts_to_translate:
            return {"error": "번역할 텍스트를 찾지 못했습니다."}

        # 3. AI 분석
        analyzer = AIAnalyzer()
        translation_map = analyzer.generate_translation_map(texts_to_translate)
        
        if not translation_map:
            return {"error": "AI가 번역 맵을 생성하지 못했습니다."}

        # 4. 물리적 PDF 텍스트 교체
        translate_text_smart(input_path, output_path, translation_map)

        # 5. 번역된 파일 반환
        return FileResponse(path=output_path, filename=output_filename, media_type='application/pdf')

    except Exception as e:
        return {"error": f"번역 중 오류가 발생했습니다: {str(e)}"}