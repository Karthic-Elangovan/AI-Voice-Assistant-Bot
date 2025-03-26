"""
AI Chatbot with Voice and Text Input using Gemini
------------------------------------------------
Features:
- Text-based chat with Google's Gemini model
- Voice input using microphone
- Text-to-speech responses
- Mode switching (text/voice)
- Session management
"""

# ======================
# 1. IMPORT LIBRARIES
# ======================
import os  # For environment variables
import streamlit as st  # Web app framework
import speech_recognition as sr  # Speech-to-text
import pyttsx3  # Text-to-speech
import threading  # Background speech processing
from dotenv import load_dotenv  # Environment variable loader
import google.generativeai as genai  # Gemini API

# Load environment variables
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

# ======================
# 2. CONFIGURATION
# ======================
# Gemini API Configuration
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-pro-latest')  

# Initialize speech recognizer
recognizer = sr.Recognizer()

# ======================
# 3. SPEECH CONTROLLER CLASS
# ======================
class SpeechController:
    """
    Handles text-to-speech conversion with background threading
    to prevent UI freezing during speech.
    """
    def __init__(self):
        self.engine = None  # TTS engine
        self.speech_thread = None  # Background thread
        self.is_speaking = False  # Speech state flag

    def speak(self, text):
        """Converts text to speech in a background thread"""
        def run_speech():
            try:
                self.is_speaking = True
                self.engine = pyttsx3.init()
                self.engine.setProperty("rate", 150)  # Words per minute
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                st.error(f"Speech synthesis error: {e}")
            finally:
                self.cleanup()
                self.is_speaking = False

        # Wait for previous speech to finish
        if self.speech_thread and self.speech_thread.is_alive():
            self.speech_thread.join()
            
        # Start new speech thread
        self.speech_thread = threading.Thread(target=run_speech, daemon=True)
        self.speech_thread.start()
    
    def stop(self):
        """Stops ongoing speech"""
        if self.is_speaking:
            self.cleanup()
            self.is_speaking = False
    
    def cleanup(self):
        """Releases speech resources"""
        if self.engine:
            self.engine.stop()
            self.engine = None

# Initialize speech controller in session state
if 'speech_controller' not in st.session_state:
    st.session_state.speech_controller = SpeechController()

# ======================
# 4. CORE FUNCTIONS
# ======================
def get_chatbot_response(user_input):
    """
    Gets AI response from Gemini API in paragraph format.
    Args:
        user_input (str): User's message
    Returns:
        str: AI generated response (paragraph format only)
    """
    try:
        # Explicit instruction for paragraph format
        paragraph_prompt = (
            f"IMPORTANT: Respond in paragraph format ONLY. Never use bullet points, dashes, numbers, "
            f"or any list formatting. Use complete sentences in a single cohesive paragraph. "
            f"Query: {user_input}\n\nResponse:"
        )
        
        # Generate content with Gemini
        response = model.generate_content(
            paragraph_prompt,
            generation_config={
                "max_output_tokens": 250,
                "temperature": 0.7,
                "top_p": 0.9
            }
        )
        
        # Additional formatting to remove any remaining bullet-like patterns
        cleaned_response = response.text.replace("•", "").replace("- ", "").strip()
        return cleaned_response
        
    except Exception as e:
        return f"Error: {str(e)}"

def get_voice_input():
    """
    Captures voice input via microphone and converts to text.
    Returns:
        str: Recognized text or None if failed
    """
    with sr.Microphone() as source:
        # Visual feedback
        status = st.empty()
        status.info("🎤 Listening... (Speak now)")
        
        try:
            # Configure microphone
            recognizer.adjust_for_ambient_noise(source, duration=1)
            
            # Listen with timeout settings
            audio = recognizer.listen(
                source,
                timeout= 5,      # Wait for speech to start
                phrase_time_limit=35  # Max recording duration
            )
            
            status.success("✓ Processing...")
            text = recognizer.recognize_google(audio)  # Google's speech-to-text
            status.empty()
            return text
            
        except sr.WaitTimeoutError:
            status.error("No speech detected")
            return None
        except sr.UnknownValueError:
            status.error("Could not understand audio")
            return None
        except Exception as e:
            status.error(f"Error: {str(e)}")
            return None

# ======================
# 5. STREAMLIT UI
# ======================
st.title("🤖 AI Voice Assistant")
st.caption("Switch between text and voice input modes")

# Initialize session state
if "current_mode" not in st.session_state:
    st.session_state.current_mode = None
    st.session_state.chat_response = ""
    st.session_state.user_input = ""
    st.session_state.is_speaking = False
    st.session_state.input_text_key = 0  # For clearing text input

def reset_app():
    """Resets all session state variables"""
    st.session_state.chat_response = ""
    st.session_state.user_input = ""
    st.session_state.is_speaking = False
    st.session_state.input_text_key += 1
    st.session_state.speech_controller.stop()

# Mode selection
mode = st.radio("Input Mode:", ["Text", "Voice"], horizontal=True)

# Reset when mode changes
if mode != st.session_state.current_mode:
    st.session_state.current_mode = mode
    reset_app()

# Global reset button
if st.button("🔄 Reset All", type="secondary"):
    reset_app()
    st.rerun()

# ======================
# 6. TEXT INPUT MODE
# ======================
if mode == "Text":
    with st.form(key="text_form"):
        # Text input with dynamic key for clearing
        user_input = st.text_input(
            "Your message:", 
            key=f"text_input_{st.session_state.input_text_key}",
            placeholder="Type here..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            submit_btn = st.form_submit_button("Send", type="primary")
        with col2:
            clear_btn = st.form_submit_button("Clear input")
        
        if submit_btn and user_input:
            st.session_state.user_input = user_input
            with st.spinner("Thinking..."):
                st.session_state.chat_response = get_chatbot_response(user_input)
        
        if clear_btn:
            st.session_state.input_text_key += 1
            st.rerun()

# ======================
# 7. VOICE INPUT MODE
# ======================
elif mode == "Voice":
    if st.button("🎤 Start Recording", type="primary"):
        user_input = get_voice_input()
        if user_input:
            st.session_state.user_input = user_input
            with st.spinner("Generating response..."):
                st.session_state.chat_response = get_chatbot_response(user_input)

# ======================
# 8. DISPLAY RESPONSE
# ======================
if st.session_state.user_input:
    st.divider()
    st.markdown(f"**You:** {st.session_state.user_input}")
    
if st.session_state.chat_response:
    st.markdown(f"**Assistant:** {st.session_state.chat_response}")
    
    # Speech controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔊 Speak Response"):
            st.session_state.speech_controller.speak(st.session_state.chat_response)
            st.session_state.is_speaking = True
    with col2:
        if st.session_state.is_speaking:
            if st.button("⏹️ Stop Speaking"):
                st.session_state.speech_controller.stop()
                st.session_state.is_speaking = False
                st.rerun()

# ======================
# 9. FOOTER
# ======================
st.divider()
st.caption("Note: Voice mode requires microphone access")