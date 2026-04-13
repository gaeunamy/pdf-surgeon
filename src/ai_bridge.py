import re
import json
from openai import OpenAI
from dotenv import load_dotenv
import fitz

load_dotenv()

class AIAnalyzer:
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-4o"
        self.system_prompt = """당신은 청구서·계약서 등 비즈니스 문서를 번역하는 전문 번역가입니다.
규칙:
1. 영어 텍스트만 한국어로 번역합니다. 이미 한국어인 부분은 그대로 유지합니다.
2. 고유명사(회사명·브랜드·이메일·URL·계좌번호·숫자·날짜)는 번역하지 말고 원문 유지.
3. 입력은 JSON 배열이며 출력도 반드시 동일 길이의 JSON 배열만 반환합니다.
4. 의미적 중복 제거: 한 줄 내에 영문과 한글이 병기된 경우, 한글 의미가 중복된다면 영문 부분은 제외하세요.
5. 절대 설명 없이 JSON 배열만 출력합니다."""
        self._eng = re.compile(r'[A-Za-z]')

    def _call_api(self, texts: list[str]) -> list[str]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"다음 텍스트를 번역하세요:\n{json.dumps(texts, ensure_ascii=False)}"}
            ],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```json\s*|^```\s*|```$", "", raw, flags=re.MULTILINE).strip()
        translated = json.loads(raw)
        return translated

    def generate_translation_map(self, full_text: str) -> dict:
        """main.py의 요구사항에 맞춰 전체 텍스트에서 번역 지도를 생성합니다."""
        # 텍스트에서 영어 문구들만 추출 (중복 제거)
        lines = [line.strip() for line in full_text.split('\n') if self._eng.search(line)]
        unique_texts = list(dict.fromkeys(lines))
        
        translation_map = {}
        batch_size = 20
        
        for i in range(0, len(unique_texts), batch_size):
            batch = unique_texts[i : i + batch_size]
            print(f"  🤖 번역 중... ({i+1}/{len(unique_texts)})")
            translated = self._call_api(batch)
            
            for orig, trans in zip(batch, translated):
                if orig != trans: # 번역이 일어난 것만 맵에 추가
                    translation_map[orig] = trans
                    print(f"    ✅ {repr(orig)} -> {repr(trans)}")
        
        return translation_map