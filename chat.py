import random
import pandas as pd
import streamlit as st
from sentence_transformers import SentenceTransformer, util
from googletrans import Translator
import asyncio
import nest_asyncio
import base64

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="CareBot: Your Health Assistant",
    page_icon="🏥",
    layout="wide"
)

# Patch the event loop to prevent "Event loop is closed" error
nest_asyncio.apply()

# Custom CSS for better UI
st.markdown("""
    <style>
    .main {
        background-color: #1E1E1E;
    }
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        color: white;
    }
    .chat-message.user {
        background-color: #2C3E50;
        border-left: 4px solid #3498DB;
    }
    .chat-message.bot {
        background-color: #2C3E50;
        border-left: 4px solid #2ECC71;
    }
    .stButton>button {
        width: 100%;
        background-color: #3498DB;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #2980B9;
    }
    .health-tip {
        background-color: #2C3E50;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #2ECC71;
        color: white;
    }
    .stMarkdown {
        color: white !important;
    }
    /* Text area styling */
    .stTextArea textarea {
        color: white !important;
        background-color: #2C3E50 !important;
        border: 2px solid #3498DB !important;
        border-radius: 0.5rem !important;
        padding: 1rem !important;
        font-size: 16px !important;
    }
    .stTextArea textarea:focus {
        border-color: #2980B9 !important;
        box-shadow: 0 0 0 1px #2980B9 !important;
    }
    .stTextArea label {
        color: white !important;
        font-weight: bold !important;
        font-size: 18px !important;
    }
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #1E1E1E;
    }
    .css-1d391kg .stMarkdown {
        color: white !important;
    }
    /* Header text */
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }
    /* Footer text */
    .footer-text {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# Load the dataset (ensure it's a .csv file, not .xlsx)
df = pd.read_csv(
    'updated_health_dataset.csv',
    names=['disease_name', 'symptoms', 'cure'],
    encoding='utf-8'
)

# Initialize SentenceTransformer model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Translator instance
translator = Translator()

# Define health tips
health_tips = {
    "sleep": [
        "Try to get at least 7-8 hours of sleep each night.",
        "Establish a regular sleep routine to improve sleep quality.",
        "Avoid screens at least 1 hour before bed to help your mind relax.",
        "Keep your bedroom cool and dark to promote better sleep.",
        "Avoid caffeine late in the day if you're having trouble sleeping.",
    ],
    "energy": [
        "Make sure you're eating a balanced diet to maintain energy.",
        "Exercise regularly to boost your energy levels.",
        "Stay hydrated throughout the day to avoid fatigue.",
        "Take short walks or stretch breaks during work to stay energized.",
        "Avoid heavy meals during the day to prevent feeling sluggish.",
    ],
    "stress": [
        "Take short breaks throughout the day to reduce stress.",
        "Practice mindfulness or meditation to help manage stress.",
        "Engage in physical activity to reduce anxiety and stress.",
        "Try journaling your thoughts to help process emotions.",
        "Listen to calming music or practice deep breathing exercises.",
    ],
    "hydration": [
        "Drink at least 8 glasses of water daily.",
        "Carry a water bottle to remind yourself to drink throughout the day.",
        "Start your day with a glass of water to activate your metabolism.",
        "Eat fruits like watermelon and oranges to help stay hydrated.",
    ],
    "diet": [
        "Eat a balanced diet rich in fruits and vegetables.",
        "Limit processed foods and added sugars.",
        "Incorporate more fiber through whole grains and legumes.",
        "Avoid skipping meals to maintain stable energy levels.",
    ],
    "mental": [
        "Practice gratitude by listing three things you're thankful for.",
        "Talk to a trusted friend or counselor if you're feeling down.",
        "Take time to do something you enjoy every day.",
        "Spend time in nature to improve mental well-being.",
    ],
    "general": [
        "Wash your hands regularly to prevent infections.",
        "Get regular health checkups and screenings.",
        "Avoid smoking and limit alcohol consumption.",
        "Protect your skin with sunscreen when going outside.",
    ],
}

# Keyword mapping
keyword_category_map = {
    "tired": "energy", "fatigue": "energy", "low energy": "energy",
    "sleep": "sleep", "insomnia": "sleep", "rest": "sleep",
    "stress": "stress", "anxious": "stress", "anxiety": "stress",
    "water": "hydration", "thirsty": "hydration", "hydration": "hydration",
    "diet": "diet", "food": "diet", "eating": "diet", "nutrition": "diet",
    "depressed": "mental", "sad": "mental", "mental": "mental",
    "general": "general",
}

# Translate text using async-safe method
def translate_text(text, dest_language='en'):
    try:
        result = translator.translate(text, dest=dest_language)
        return result.text
    except Exception as e:
        return f"Translation failed: {str(e)}"

# Personalized tip
def get_personalized_health_tip(user_input, disease_info=None):
    user_input_lower = user_input.lower()
    selected_category = None
    
    # First check if we have disease information
    if disease_info and "Disease:" in disease_info:
        disease_name = disease_info.split("Disease:")[1].split("\n")[0].strip().lower()
        cure = disease_info.split("Recommended Cure:")[1].strip().lower()
        
        # Map disease-specific keywords to categories
        disease_keywords = {
            "fever": "general",
            "cold": "general",
            "flu": "general",
            "headache": "general",
            "diabetes": "diet",
            "hypertension": "diet",
            "obesity": "diet",
            "anxiety": "mental",
            "depression": "mental",
            "insomnia": "sleep",
            "fatigue": "energy",
            "dehydration": "hydration",
            "stress": "stress"
        }
        
        # Check if any disease keywords match
        for keyword, category in disease_keywords.items():
            if keyword in disease_name or keyword in cure:
                selected_category = category
                break
    
    # If no disease-specific category found, check user input keywords
    if not selected_category:
        for keyword, category in keyword_category_map.items():
            if keyword in user_input_lower:
                selected_category = category
                break
    
    # If still no category found, use general
    if not selected_category:
        selected_category = "general"
    
    # Get 3 different tips from the selected category
    available_tips = health_tips[selected_category].copy()
    selected_tips = []
    
    # If we have less than 3 tips available, we'll use what we have
    num_tips = min(3, len(available_tips))
    
    for _ in range(num_tips):
        if available_tips:
            tip = random.choice(available_tips)
            selected_tips.append(tip)
            available_tips.remove(tip)  # Remove to avoid repetition
    
    return selected_tips

# Best cure matcher
def find_best_cure(user_input):
    user_input_embedding = model.encode(user_input, convert_to_tensor=True)
    symptom_embeddings = model.encode(df['symptoms'].tolist(), convert_to_tensor=True)

    similarities = util.pytorch_cos_sim(user_input_embedding, symptom_embeddings)[0]
    best_match_idx = similarities.argmax().item()
    best_match_score = similarities[best_match_idx].item()
    SIMILARITY_THRESHOLD = 0.5

    if best_match_score < SIMILARITY_THRESHOLD:
        return "I'm sorry, I don't have enough information on this. Please consult a healthcare professional."

    matched_row = df.iloc[best_match_idx]
    return f"Possible Disease: {matched_row['disease_name']}\n\nRecommended Cure: {matched_row['cure']}"

# Header with logo and title
# col1, col2 = st.columns([1, 3])
# with col2:
st.title("CareBot: Your Health Assistant")
st.markdown("Your AI-powered health companion for personalized medical advice and wellness tips.")

# Sidebar for language selection
with st.sidebar:
    st.header("Settings")
    language_choice = st.selectbox(
        "Select Language",
        ["English", "Hindi", "Gujarati", "Korean", "Turkish",
         "German", "French", "Arabic", "Urdu", "Tamil", "Telugu", "Chinese", "Japanese"]
    )
    
    st.markdown("---")
    st.markdown("### About CareBot")
    st.markdown("""
    CareBot is an AI-powered health assistant that provides:
    - Personalized health advice
    - Disease information
    - Wellness tips
    - Multi-language support
    """)

# Main chat interface
st.markdown("### Ask Your Health Question")
user_input = st.text_area(
    "Type your health-related question here:",
    height=100,
    placeholder="Example: I have been experiencing headaches and fatigue for the past few days...",
    help="Please describe your symptoms or health concern in detail"
)

language_codes = {
    "English": "en", "Hindi": "hi", "Gujarati": "gu", "Korean": "ko", "Turkish": "tr",
    "German": "de", "French": "fr", "Arabic": "ar", "Urdu": "ur", "Tamil": "ta",
    "Telugu": "te", "Chinese": "zh-CN", "Japanese": "ja"
}

if st.button("Get Health Advice", key="submit"):
    if user_input:
        # Create a container for the chat
        chat_container = st.container()
        
        with chat_container:
            # User message
            st.markdown(f"""
            <div class="chat-message user">
                <strong>You:</strong><br>
                {user_input}
            </div>
            """, unsafe_allow_html=True)
            
            # Disease response
            response = find_best_cure(user_input)
            translated_response = translate_text(response, dest_language=language_codes[language_choice])
            
            # Bot message with disease info
            st.markdown(f"""
            <div class="chat-message bot">
                <strong>CareBot:</strong><br>
                {translated_response}
            </div>
            """, unsafe_allow_html=True)
            
            # Health tips
            personalized_tips = get_personalized_health_tip(user_input, response)
            st.markdown("### 💡 Personalized Health Tips")
            
            for i, tip in enumerate(personalized_tips, 1):
                translated_tip = translate_text(tip, dest_language=language_codes[language_choice])
                st.markdown(f"""
                <div class="health-tip">
                    <strong>Tip {i}:</strong> {translated_tip}
                </div>
                """, unsafe_allow_html=True)
    else:
        st.warning("Please enter your health question first!")

