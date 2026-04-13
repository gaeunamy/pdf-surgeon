import sys
import os

# 프로젝트 루트 경로를 찾아서 src 폴더를 불러올 수 있게 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.engine import mask_text

if __name__ == "__main__":
    # 경로 설정 (project_root 기준 완벽한 절대 경로)
    INPUT_PDF = os.path.join(project_root, "data", "input", "sample.pdf")
    OUTPUT_PDF = os.path.join(project_root, "data", "output", "masked_sample.pdf")
    
    # 지우고 싶은 텍스트(기호 포함) 지정
    TARGET_TEXT = "홍길동 (Hong Gil-dong)"
    
    # 마스킹(Redact) 엔진 실행
    mask_text(INPUT_PDF, OUTPUT_PDF, TARGET_TEXT)