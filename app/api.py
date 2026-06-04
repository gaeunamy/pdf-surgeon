from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import json

from src import engine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://pdf-surgeon-xi.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.post("/translate/")
async def translate_pdf(
    file: UploadFile = File(...),
    mode: str = Form("smart"),
    manual_dict: str = Form("{}"),
    target_word: str = Form("")
):
    try:
        # 1. 업로드된 원본 PDF 파일 읽기
        pdf_bytes = await file.read()
        
        # 2. 화면에서 보낸 수동 단어장을 파이썬 딕셔너리로 변환
        translation_dict = json.loads(manual_dict)

        # 3. 모드에 따라 엔진 가동
        if mode == "smart":
            print("🧠 지능형 번역 엔진 가동 중...")
            result_pdf = engine.translate_text_smart(pdf_bytes)
            
        elif mode == "manual":
            print(f"✍️ 수동 번역 엔진 가동 중... (사전: {translation_dict})")
            result_pdf = engine.translate_text_manual(pdf_bytes, translation_dict)
            
        elif mode == "mask":
            print(f"⬛ 마스킹 엔진 가동 중... (가릴 단어: {target_word})")
            # 입력받은 target_word를 마스킹 엔진으로 넘김
            result_pdf = engine.create_masked_pdf(pdf_bytes, target_text=target_word)
            
        else:
            raise HTTPException(status_code=400, detail="알 수 없는 모드입니다.")

        # 4. 번역된 PDF 파일을 반환
        return Response(content=result_pdf, media_type="application/pdf")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))