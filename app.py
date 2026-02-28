import streamlit as st
import openai
import requests
from bs4 import BeautifulSoup
from streamlit_mic_recorder import mic_recorder
import io, base64, pandas as pd
from PIL import Image
import fitz  # PyMuPDF

# --- 頁面配置 ---
st.set_page_config(page_title="BridgeAI Pro", layout="wide")

# --- 側邊欄：設定與單字本 ---
with st.sidebar:
    st.title("⚙️ BridgeAI 控制塔")
    api_key = st.text_input("OpenAI API Key", type="password")
    difficulty = st.select_slider("難度等級", options=["Beginner", "Intermediate", "Advanced", "Automatic"], value="Automatic")
    
    st.divider()
    st.subheader("📓 我的單字本")
    if "vocab_list" not in st.session_state:
        st.session_state.vocab_list = []
    
    if st.session_state.vocab_list:
        df_vocab = pd.DataFrame(st.session_state.vocab_list)
        st.dataframe(df_vocab, use_container_width=True)
        csv = df_vocab.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 下載單字本 (CSV)", data=csv, file_name="my_vocab.csv", mime="text/csv")
    else:
        st.write("目前尚無存取的單字")

# --- 核心功能函數 ---

def process_file_input(uploaded_file):
    """處理 PDF 或 圖片轉文字"""
    client = openai.OpenAI(api_key=api_key)
    if uploaded_file.type == "application/pdf":
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        text = " ".join([page.get_text() for page in doc])
        return text
    else:
        # 使用 GPT-4o 進行視覺辨識 (OCR)
        img = Image.open(uploaded_file)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": [
                {"type": "text", "text": "Extract all English text from this image accurately."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ]}]
        )
        return response.choices.message.content

def get_ai_feedback_and_vocab(user_text):
    """獲取視覺化評分與單字建議"""
    client = openai.OpenAI(api_key=api_key)
    prompt = f"""
    Evaluate this English input: "{user_text}"
    1. Feedback: Return an HTML string where incorrect words are <span style='color:red'>red</span> and corrections are <span style='color:green'>green</span>.
    2. Vocabulary: Extract 2 challenging words from the material, provide [Word, Definition in Chinese, Example].
    3. Next Question: Ask one question based on the material.
    Return JSON format: {{"html_feedback": "...", "vocab": [{{...}}, {{...}}], "next_question": "..."}}
    """
    res = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": prompt}], response_format={ "type": "json_object" })
    import json
    return json.loads(res.choices.message.content)

# --- 主介面 ---
st.title("🚀 BridgeAI Pro: 聽說讀寫全方位練習")

# 1. 多模態素材導入 (Multi-modal Import)
tab1, tab2 = st.tabs(["🌐 網頁/文字導入", "📄 PDF/圖片導入"])
with tab1:
    url_input = st.text_input("貼上連結或文字：")
    if st.button("確認導入"):
        if url_input.startswith("http"):
            res = requests.get(url_input)
            soup = BeautifulSoup(res.text, 'html.parser')
            st.session_state.current_material = " ".join([p.get_text() for p in soup.find_all('p')[:3]])
        else: st.session_state.current_material = url_input
        st.success("素材已就緒")

with tab2:
    uploaded_file = st.file_uploader("上傳 PDF 或 課本照片", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded_file and st.button("掃描並導入"):
        with st.spinner("辨識中..."):
            st.session_state.current_material = process_file_input(uploaded_file)
            st.write("**辨識內容摘要：**", st.session_state.current_material[:200] + "...")

st.divider()

# 2. 互動區
col_chat, col_feedback = st.columns([2, 1])

with col_chat:
    st.subheader("💬 對話練習")
    audio_data = mic_recorder(start_prompt="🎤 錄音回答", stop_prompt="⏹️ 送出", key='pro_recorder')
    
    if audio_data and api_key:
        # STT -> GPT -> TTS
        client = openai.OpenAI(api_key=api_key)
        user_text = client.audio.transcriptions.create(model="whisper-1", file=io.BytesIO(audio_data['bytes']).name=="audio.mp3" and io.BytesIO(audio_data['bytes'])).text
        
        data = get_ai_feedback_and_vocab(user_text)
        
        # 顯示回饋與自動播放語音
        st.session_state.last_feedback = data['html_feedback']
        st.session_state.vocab_list.extend(data['vocab'])
        
        st.chat_message("user").write(user_text)
        st.chat_message("assistant").write(data['next_question'])
        
        # TTS 自動播放
        tts_res = client.audio.speech.create(model="tts-1", voice="nova", input=data['next_question'])
        b64_audio = base64.b64encode(tts_res.read()).decode()
        st.markdown(f'<audio autoplay src="data:audio/mp3;base64,{b64_audio}">', unsafe_allow_html=True)

with col_feedback:
    st.subheader("📊 視覺化評分")
    if "last_feedback" in st.session_state:
        st.markdown(f"<div style='background:#f0f2f6; pading:10px; border-radius:10px;'>{st.session_state.last_feedback}</div>", unsafe_allow_html=True)
        st.caption("🔴 紅色為誤用，🟢 綠色為建議寫法")
