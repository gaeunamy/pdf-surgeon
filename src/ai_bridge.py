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
        self.system_prompt = """당신은 비즈니스 문서 전문 번역가입니다.
규칙:
1. 문서의 '항목명(Label)'은 반드시 한국어로 번역하세요. (예: Date -> 날짜, Address -> 주소)
2. 항목에 해당하는 '값(Value)' 중 고유명사, 숫자, 이메일, 계좌번호만 원문을 유지하세요.
3. 한 줄 내에 영문과 한글이 병기되어 의미가 중복된다면 한글만 남기되, 새로운 정보가 포함된 영문은 번역하여 포함하세요.
4. 입력과 동일한 크기의 JSON 배열로 출력하세요."""
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