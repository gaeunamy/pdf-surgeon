import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from src.engine import mask_text

if __name__ == "__main__":
    mask_text("../data/input/sample.pdf", "../data/output/masked_sample.pdf", "홍길동 (Hong Gil-dong)")