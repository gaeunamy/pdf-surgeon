import sys
import os
import fitz

# 프로젝트 루트 경로를 찾아서 src 폴더를 불러올 수 있게 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.engine import translate_text_manual

if __name__ == "__main__":
    # 경로 설정
    INPUT_PDF = os.path.join(project_root, "data", "input", "sample.pdf")
    OUTPUT_PDF = os.path.join(project_root, "data", "output", "translated_sample.pdf")
    
    # 번역 맵 정의
    MY_MAP = {
        "INVOICE (청구서)": "세금계산서 (INVOICE) (청구서)",
        "Date": "날짜", 
        "Account Number:": "계좌번호", # 콜론 유지하는지 확인
    }
    
    # 엔진 실행
    translate_text_manual(INPUT_PDF, OUTPUT_PDF, MY_MAP)