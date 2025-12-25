import streamlit as st
import google.generativeai as genai
from datetime import datetime
from gtts import gTTS
import io

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="CBSE Commerce Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE ---
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hello! I am your Commerce Coach. Ready to start your 3-hour study session?"}]
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
    """
    Removes markdown symbols so the voice doesn't say 'Dash Dash' or 'Asterisk'.
    """
    # 1. Remove Horizontal Lines (---)
    text = text.replace("---", "")
    text = text.replace("___", "")
    
    # 2. Remove Bold/Italic markers (* and _)
    text = text.replace("*", "")
    text = text.replace("_", "")
    
    # 3. Remove Headings (#)
    text = text.replace("#", "")
    
    # 4. Remove Code blocks (`)
    text = text.replace("`", "")
    
    # 5. Remove extra spaces created by deletion
    text = " ".join(text.split())
    
    return text

# --- SIDEBAR ---
with st.sidebar:
    st.title("Study Dashboard")
    api_key = st.text_input("Gemini API Key:", type="password")

    # SETTINGS
    st.markdown("### ⚙️ Settings")
    voice_on = st.checkbox("🔊 Voice Mode (Indian Accent)", value=False)
    concise_mode = st.checkbox("⚡ Concise / Revision Mode", value=False)
    
    st.markdown("---")

    # PROFILE
    st.subheader("👤 Profile")
    student_name = st.text_input("Name", value="Priya Sharma")
    student_class = st.radio("Class", ["Class 11", "Class 12"], horizontal=True)

    st.markdown("---")

    # TIMER
    st.subheader("⏳ 3-Hour Schedule")
    if not st.session_state.study_session_active:
        st.info("Goal: 3 Hours (30m Study / 5m Break)")
        if st.button("🚀 Start Study Session"):
            st.session_state.study_session_active = True
            st.session_state.start_time = datetime.now()
            st.rerun()
    else:
        status, time_val = get_session_status()
        if status == "FINISHED":
            st.success("🎉 Session Complete!")
            if st.button("Reset"):
                st.session_state.study_session_active = False
                st.session_state.start_time = None
                st.rerun()
        elif status == "BREAK":
            st.warning(f"☕ BREAK TIME ({5 - time_val}m left)")
        elif status == "STUDY":
            st.success(f"📚 STUDY TIME ({30 - time_val}m left)")
            st.progress(time_val / 30)
        
        if st.button("🛑 Stop"):
            st.session_state.study_session_active = False
            st.session_state.start_time = None
            st.rerun()

    st.markdown("---")
    subject_mode = st.selectbox("Current Subject", ["Accountancy 📊", "Economics 💰", "Business Studies 💼"])
    st.session_state.last_subject = subject_mode

    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- MAIN APP ---
st.title("🎓 The Commerce Coach")

# Break Alert
current_status, _ = get_session_status()
if st.session_state.study_session_active and current_status == "BREAK":
    st.info("☕ BREAK TIME! Step away from the screen.")

# History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt = st.chat_input("Ask a doubt...")

if prompt:
    if not api_key:
        st.error("Enter API Key in sidebar.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        genai.configure(api_key=api_key)
        
        # MODEL FINDER
        found_model = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                found_model = m.name
                break 
        if not found_model: st.error("❌ No AI models found.")
        
        # PROMPT LOGIC
        length_instruction = "Give detailed explanations with examples."
        if concise_mode:
            length_instruction = "BE EXTREMELY CONCISE. Summarize in less than 60 words."

        if "Accountancy" in subject_mode:
            focus_prompt = "Focus on Journal Entries, Ledgers. Use Tables."
        elif "Economics" in subject_mode:
            focus_prompt = "Focus on Graphs and differences."
        else:
            focus_prompt = "Focus on Case Studies and Keywords."

        system_instruction = f"""
        You are an Indian Commerce Tutor for {student_name}, {student_class}.
        SUBJECT: {subject_mode}. 
        INSTRUCTION: {length_instruction}
        RULES: {focus_prompt} Strictly NCERT context.
        """

        model = genai.GenerativeModel(model_name=found_model, system_instruction=system_instruction)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = model.generate_content(prompt)
                st.markdown(response.text)
                
                # VOICE GENERATION
                if voice_on:
                    try:
                        speak_text = clean_text_for_speech(response.text)
                        tts = gTTS(text=speak_text, lang='
