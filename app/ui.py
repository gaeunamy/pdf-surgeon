import streamlit as st
import requests

# 페이지 기본 설정
st.set_page_config(page_title="PDF AI 번역기", page_icon="📄", layout="centered")

st.title("📄 지능형 PDF 번역 서비스")
st.write("영문 PDF 문서를 업로드하면, 폰트와 레이아웃을 보호하며 한글로 번역해 드립니다.")

# 파일 업로드 버튼
uploaded_file = st.file_uploader("여기에 PDF 파일을 드래그 앤 드롭하세요.", type=["pdf"])

if uploaded_file is not None:
    st.info(f"선택된 파일: {uploaded_file.name}")
    
    # 번역 실행 버튼
    if st.button("🚀 번역 시작하기", use_container_width=True):
        with st.spinner("AI가 문서를 분석하고 번역하는 중입니다... (문서 크기에 따라 1~2분 소요될 수 있습니다)"):
            
            # FastAPI 서버로 파일 전송 준비
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            
            try:
                # 같은 도커 컨테이너 안에서 돌아가는 FastAPI(8000번 포트) 호출
                response = requests.post("http://127.0.0.1:8000/translate/", files=files)

                if response.status_code == 200:
                    st.success("✨ 번역이 완료되었습니다!")
                    
                    # 다운로드 버튼 생성
                    st.download_button(
                        label="📥 번역된 PDF 다운로드",
                        data=response.content,
                        file_name=f"translated_{uploaded_file.name}",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                else:
                    st.error(f"⚠️ 서버 오류가 발생했습니다. (상태 코드: {response.status_code})")
                    st.write(response.json())
                    
            except Exception as e:
                st.error(f"통신 중 오류가 발생했습니다: {str(e)}")