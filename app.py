import streamlit as st
import google.generativeai as genai
from datetime import datetime
from gtts import gTTS
import io

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="Commerce Tutor (macOS Edition)",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 🎨 MACBOOK THEME CSS ---
def apply_mac_theme():
    st.markdown("""
        <style>
        /* 1. FORCE APPLE FONTS */
        html, body, [class*="css"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        
        /* 2. ROUNDED CORNERS & SOFT SHADOWS (The "Mac" Look) */
        .stTextInput > div > div > input, 
        .stSelectbox > div > div > div {
            border-radius: 12px !important;
            border: 1px solid #E5E5EA !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
        }
        
        /* 3. BUTTONS: Apple Blue Pills */
        .stButton > button {
            border-radius: 20px !important;
            background-color: #007AFF !important; /* Apple Blue */
            color: white !important;
            border: none !important;
            padding: 10px 24px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease;
        }
        .stButton > button:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 12px rgba(0,122,255,0.3);
        }

        /* 4. IMESSAGE STYLE CHAT BUBBLES */
        /* User Message (Blue) */
        [data-testid="stChatMessage"]:nth-child(odd) {
            background-color: #007AFF15; /* Light Blue tint */
            border-radius: 18px;
            border-bottom-right-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
        }
        /* Assistant Message (Gray) */
        [data-testid="stChatMessage"]:nth-child(even) {
            background-color: #F2F2F7; /* Apple Gray */
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            padding: 10px;
            margin-bottom: 10px;
        }
        
        /* 5. SIDEBAR STYLING */
        [data-testid="stSidebar"] {
            background-color: #FBFBFD; /* Very light gray */
            border-right: 1px solid #E5E5EA;
        }
        </style>
    """, unsafe_allow_html=True)

# Apply the theme immediately
apply_mac_theme()

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your Commerce Coach. Ready to start?"}]
if "study_session_active" not in st.session_state:
    st.session_state.study_session_active = False
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "last_subject" not in st.session_state:
    st.session_state.last_subject = None

# --- HELPER FUNCTIONS ---
def get_session_status():
    if not st.session_state.start_time: return None, 0
    now = datetime.now()
    elapsed = now - st.session_state.start_time
    total_minutes = int(elapsed.total_seconds() / 60)
    if total_minutes >= 180: return "FINISHED", total_minutes
    cycle_time = total_minutes % 35
    if cycle_time < 30: return "STUDY", cycle_time 
    else: return "BREAK", cycle_time - 30 

def clean_text_for_speech(text):
    text = text.replace("---", "").replace("___", "")
    text = text.replace("*", "").replace("_", "")
    text = text.replace("#", "").replace("`", "")
    text = " ".join(text.split())
    return text

# --- SIDEBAR DASHBOARD ---
with st.sidebar:
    st.title("🖥️ Study Control") # Changed icon
    api_key = st.text_input("Gemini API Key:", type="password")

    st.markdown("### ⚙️ Preferences")
    voice_on = st.checkbox("🔊 Indian Voice Tutor", value=False)
    concise_mode = st.checkbox("⚡ Quick Summary Mode", value=False)
    
    st.markdown("---")

    st.subheader("👤 Student Profile")
    student_name = st.text_input("Name", value="Priya Sharma")
    student_class = st.radio("Class", ["Class 11", "Class 12"], horizontal=True)

    st.markdown("---")

    st.subheader("⏳ Pomodoro Timer")
    if not st.session_state.study_session_active:
        st.info("Target: 3 Hours")
        if st.button("🚀 Launch Session"):
            st.session_state.study_session_active = True
            st.session_state.start_time = datetime.now()
            st.rerun()
    else:
        status, time_val = get_session_status()
        if status == "FINISHED":
            st.success("🎉 Target Reached!")
            if st.button("Reset Timer"):
                st.session_state.study_session_active = False
                st.session_state.start_time = None
                st.rerun()
        elif status == "BREAK":
            st.warning(f"☕ Break Time ({5 - time_val}m)")
        elif status == "STUDY":
            st.success(f"📚 Focus Time ({30 - time_val}m)")
            st.progress(time_val / 30)
        
        if st.button("🛑 Pause"):
            st.session_state.study_session_active = False
            st.session_state.start_time = None
            st.rerun()

    st.markdown("---")
    subject_mode = st.selectbox("Select Subject", ["Accountancy 📊", "Economics 💰", "Business Studies 💼"])
    st.session_state.last_subject = subject_mode

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- MAIN INTERFACE ---
st.title(" Commerce Tutor Pro") # Apple Style Title

# Break Overlay
current_status, _ = get_session_status()
if st.session_state.study_session_active and current_status == "BREAK":
    st.info("☕ It's Break Time. Relax for 5 minutes.")

# Render Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
prompt = st.chat_input("Type your doubt here...")

if prompt:
    if not api_key:
        st.error("⚠️ Please enter your API Key in the sidebar.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        genai.configure(api_key=api_key)
        
        # FIND MODEL
        found_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                found_model = m.name
                break 
        if not found_model: st.error("❌ No AI models found.")
        
        # INSTRUCTIONS
        length_instruction = "Explain simply with clear examples."
        if concise_mode:
            length_instruction = "Be extremely concise. Bullet points only. <60 words."

        if "Accountancy" in subject_mode:
            focus_prompt = "Focus on Journal Entries, Ledgers. Use tables."
        elif "Economics" in subject_mode:
            focus_prompt = "Focus on Graphs, curves, and definitions."
        else:
            focus_prompt = "Focus on Keywords and Case Studies."

        system_instruction = f"""
        You are an Indian Commerce Tutor for {student_name}, {student_class}.
        Subject: {subject_mode}. 
        Style: {length_instruction}
        Focus: {focus_prompt}. Strictly NCERT based.
        """

        model = genai.GenerativeModel(model_name=found_model, system_instruction=system_instruction)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = model.generate_content(prompt)
                st.markdown(response.text)
                
                # VOICE
                if voice_on:
                    try:
                        speak_text = clean_text_for_speech(response.text)
                        tts = gTTS(text=speak_text, lang='en', tld='co.in', slow=False)
                        audio_data = io.BytesIO()
                        tts.write_to_fp(audio_data)
                        st.audio(audio_data, format='audio/mp3')
                    except:
                        st.caption("🔇 Voice unavailable (Check Internet)")

        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Error: {e}")
