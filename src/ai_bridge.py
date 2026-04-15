import json
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에서 OPENAI_API_KEY 로드
load_dotenv()

class AIAnalyzer:
    def __init__(self):
        self.client = OpenAI()
        self.model = "gpt-4o" # 최신 모델 사용
        
        # AI에게 부여할 명확한 역할과 JSON 출력 강제
        self.system_prompt = """
        당신은 비즈니스 및 전문 문서 번역 AI입니다.
        사용자가 제공한 텍스트 배열을 한국어로 자연스럽게 번역하세요.
        
        [번역 규칙]
        1. 고유명사, 숫자, 이메일, 웹사이트 주소는 원문 그대로 유지하세요.
        2. 문서의 레이아웃 유지를 위해 기호(: , . - 등)와 공백은 최대한 원문과 동일하게 유지하세요.
        3. 의미가 없는 단순 기호나 알파벳 단일 글자는 번역하지 마세요.
        
        [출력 규칙 - 중요]
        반드시 {"원문1": "번역문1", "원문2": "번역문2"} 형태의 JSON 객체(Object) 형식으로만 응답하세요.
        """

    def generate_translation_map(self, text_list: list[str]) -> dict:
        """텍스트 리스트를 받아 영문->한글 번역 맵(dict)을 반환합니다."""
        if not text_list:
            return {}

        print(f"  🤖 OpenAI API 호출 중... (총 {len(text_list)}개 텍스트 덩어리 번역)")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": json.dumps(text_list, ensure_ascii=False)}
                ],
                response_format={"type": "json_object"}, # JSON 형태로 확실히 받기
                temperature=0.1, # 번역의 일관성을 위해 낮은 온도 설정
            )
            
            # API 응답 파싱
            result_content = response.choices[0].message.content
            translation_map = json.loads(result_content)
            
            # 원문과 번역문이 똑같거나 빈 문자열인 경우 필터링하여 최적화
            optimized_map = {
                orig: trans for orig, trans in translation_map.items() 
                if orig.strip() != trans.strip() and trans.strip()
            }
            return optimized_map
            
        except Exception as e:
            print(f"❌ OpenAI API 호출 중 오류 발생: {e}")
            return {}