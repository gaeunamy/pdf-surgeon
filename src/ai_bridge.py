import json
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class AIBridge:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        print(f"🔑 API Key Loaded: {api_key[:10]}..." if api_key else "❌ API Key Missing!")
        self.client = OpenAI(api_key=api_key)

    def get_translation_map(self, text_list):
        if not text_list: return {}
        print(f"🤖 AI 분석 시작...")
        try:
            system_msg = (
                "Translate each English item to Korean. "
                "Input is a JSON array of English strings. "
                "Return a JSON object where Key is the exact input string and Value is the Korean translation. "
                "Never skip any item. Never leave value empty."
            )
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": json.dumps(text_list, ensure_ascii=False)}
                ],
                response_format={"type": "json_object"}
            )
            res = json.loads(response.choices[0].message.content)
            print(f"✅ AI 단어장 생성 완료: {res}")
            return res
        except Exception as e:
            print(f"❌ AI Bridge 에러: {str(e)}")
            return {}

bridge = AIBridge()