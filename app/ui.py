import streamlit as st
import requests
import json

st.set_page_config(page_title="PDF-SURGEON", page_icon="🩺", layout="centered")

st.title("📄 지능형 PDF 번역 서비스")

st.markdown("### ⚙️ 작업 모드 선택")
mode_display = st.radio(
    "어떤 방식으로 PDF를 처리할까요?",
    ["🧠 지능형 번역 (Smart)", "✍️ 수동 번역 (Manual)", "⬛ 단어 마스킹 (Masking)"],
    horizontal=True
)

mode_map = {
    "🧠 지능형 번역 (Smart)": "smart",
    "✍️ 수동 번역 (Manual)": "manual",
    "⬛ 단어 마스킹 (Masking)": "mask"
}
selected_mode = mode_map[mode_display]

if 'dict_rows' not in st.session_state:
    st.session_state.dict_rows = 3

manual_dict = {}
target_mask_word = ""  # 마스킹 단어 변수 추가

# 1. 수동 모드 UI
if selected_mode == "manual":
    st.markdown("### 📖 수동 번역 단어장")
    for i in range(st.session_state.dict_rows):
        col1, col2 = st.columns(2)
        
        p_src = "ex) 바꾸고 싶은 단어" if i == 0 else ""
        p_tgt = "ex) 대치할 단어" if i == 0 else ""
        
        with col1:
            src = st.text_input(f"원래 단어_{i}", key=f"src_{i}", placeholder=p_src, label_visibility="collapsed")
        with col2:
            tgt = st.text_input(f"바꿀 단어_{i}", key=f"tgt_{i}", placeholder=p_tgt, label_visibility="collapsed")
            
        if src and tgt:
            manual_dict[src.strip()] = tgt.strip()
    
    if st.button("➕ 단어 추가하기"):
        st.session_state.dict_rows += 1
        st.rerun()

# 2. 마스킹 모드 UI
elif selected_mode == "mask":
    st.markdown("### ⬛ 가릴 단어 지정")
    target_mask_word = st.text_input("PDF에서 가리고 싶은 단어를 1개 입력해 주세요.", placeholder="ex) 이름, 전화번호, 주소 등")

st.divider()

uploaded_file = st.file_uploader("여기에 PDF 파일을 드래그 앤 드롭하세요.", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 실행하기", use_container_width=True):
        
        # 빈칸 입력 방어 로직
        if selected_mode == "manual" and not manual_dict:
            st.warning("⚠️ 수동 번역을 위해 최소 한 쌍 이상의 단어를 입력해 주세요!")
        elif selected_mode == "mask" and not target_mask_word:
            st.warning("⚠️ 마스킹할 단어를 입력해 주세요!")
        else:
            with st.spinner("AI가 문서를 분석하고 처리하는 중입니다..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                
                # 서버로 보낼 때 target_word도 같이 보냄
                data = {
                    "mode": selected_mode,
                    "manual_dict": json.dumps(manual_dict),
                    "target_word": target_mask_word.strip() 
                }
                
                try:
                    response = requests.post("http://127.0.0.1:8000/translate/", files=files, data=data)

                    if response.status_code == 200:
                        st.success("✨ 작업이 완료되었습니다!")
                        st.download_button(
                            label="📥 결과 PDF 다운로드",
                            data=response.content,
                            file_name=f"result_{uploaded_file.name}",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True
                        )
                    else:
                        st.error("⚠️ 서버 오류가 발생했습니다.")
                        st.write(response.json())
                        
                except Exception as e:
                    st.error(f"통신 중 오류가 발생했습니다: {str(e)}")