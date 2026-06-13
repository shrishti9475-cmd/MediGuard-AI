import base64
import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
import fitz # PyMuPDF
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
import database as db

# --- 1. SETUP & LLM INITIALIZATION ---
load_dotenv()

print("ElevenLabs key loaded:", bool(os.getenv("ELEVENLABS_API_KEY")))

from tavily import TavilyClient
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

from elevenlabs.client import ElevenLabs
client = ElevenLabs(
    api_key=os.getenv("ELEVENLABS_API_KEY")
)
print("AGENT FILE:", __file__)
print("Client type:", type(client))
print("CLIENT ATTRS:", dir(client))


print("Current folder:", os.getcwd())


# Groq Llama 3 Model Setup
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# --- 2. SYSTEM PROMPT (Guardrails) ---

system_prompt = """You are a highly empathetic, professional Indian Healthcare AI Assistant. 
Your core jobs are:
1. Tracking medications and fitness.
2. Analyzing medical reports using your tools.
3. Suggesting culturally relevant Indian diet and yoga based on health data.
4. Comparing medicines for safety and salt clashes.

CRITICAL RULES:
- GREETINGS: You can reply normally to greetings (Hi, Hello).
- MEDICINES: If the user asks to compare medicines, drugs, or salts (e.g., Dolo, Crocin, Paracetamol) EVEN IF MISSPELLED (like 'crosin'), YOU MUST NOT BLOCK IT. This is a valid medical query. You MUST use the 'compare_medicine_safety_tool' immediately.
- REPORTS: Use the 'analyze_medical_report_tool' for report text.
- STRICT BLOCK: ONLY block completely non-medical topics (like politics, movies, coding, cars) by saying EXACTLY: "I am a specialized Health & Wellness Assistant. I can only help you with medical, fitness, and health-related queries." Do NOT block anything related to pain, symptoms, or medicines.
"""

# --- 3. ALL TOOLS ---
@tool
def medical_search_tool(query: str):
    """
    Search latest medical information
    """
    results = tavily.search(
        query=query,
        search_depth="advanced",
        max_results=5
    )
    return str(results)

@tool
def add_medication_tool(name: str, time: str):
    """Use this tool to add a new medication to the patient's schedule."""
    db.add_medicine(name, time)
    return f"Successfully added {name} at {time} to the database."

@tool
def log_fitness_tool(activity: str, duration: str):
    """Use this tool to log a physical activity, workout, or exercise."""
    db.add_fitness_log(activity, duration)
    return f"Successfully logged {duration} of {activity}."

@tool
def log_symptom_tool(symptom_description: str):
    """Use this tool when the user mentions a health issue, pain, or symptom."""
    db.add_symptom(symptom_description)
    return f"I've noted down your symptom: {symptom_description}. Please monitor it."

@tool
def analyze_medical_report_tool(report_text: str):
    """Use this tool to analyze the text extracted from a patient's medical report."""
    analysis_prompt = f"Analyze this medical report text. Explain any abnormal values simply. Suggest Indian diet/yoga. Text: {report_text[:1500]}"
    return analysis_prompt

@tool
def compare_medicine_safety_tool(old_medicine: str, new_medicine: str):
    """Use this tool to compare two medicines. Checks for duplicate salts and harmful interactions."""
    comparison_prompt = f"Compare these two medicines: {old_medicine} and {new_medicine}. Check for duplicate salts (e.g. Paracetamol in both) and harmful interactions. Provide a clear 'Safe' or 'Warning' advice for an Indian patient."
    return comparison_prompt

# --- 4. BINDING TOOLS ---
tools = [
    add_medication_tool, 
    log_fitness_tool, 
    log_symptom_tool,
    analyze_medical_report_tool, 
    compare_medicine_safety_tool,
    medical_search_tool
]

# --- 5. CREATING THE AGENT ---
# 🔥 THE FIX 1: Removed 'state_modifier' to match your LangGraph version!
agent_executor = create_react_agent(llm, tools)
# --- 5.5 THE PERSONA ENGINE (Soul Mode) ---
# Yahan hum alag-alag characters (prompts) define kar rahe hain
EMERGENCY_WORDS = [
    "chest pain",
    "heart attack",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "stroke",
    "unconscious",
    "blood vomiting",
    "severe bleeding"
]
PERSONAS = {
    "🩺 Medical": """You are a highly empathetic, professional Indian Healthcare AI Assistant. 
    Your core jobs are:
    1. Tracking medications and fitness.
    2. Analyzing medical reports.
    3. Suggesting culturally relevant Indian diet and yoga based on health data.
    
    [CONVERSATION ROUTING & BOUNDARY RULES]
    You must classify the user's input and respond according to these 3 strict rules:
    
    1. GREETINGS (ALLOW): If the user simply says "hi", "hello", "good morning", "hey", "kaise ho", or basic small talk, DO NOT refuse them. Respond warmly, politely, and invite them to ask a health or wellness-related question.
    2. HEALTH TOPICS (ALLOW): If the query is about medicine, fitness, diet, hygiene, human body, medical reports, or wellness, answer helpfully, safely, and professionally.
    3. IRRELEVANT / NON-HEALTH (STRICT REFUSAL): If the user asks about politics, coding, history, finance, wars, entertainment, or any non-health topic, OR uses vulgar/abusive language, you MUST STRICTLY REFUSE. Do NOT answer the question. Reply EXACTLY with this: 
    "🙏 I am a specialized Health & Wellness AI. I can only assist you with medical, fitness, hygiene, and diet-related queries. How can I help you with your health today?"
    
    [CRITICAL RULE FOR LOGGING DATA]
    If the user explicitly tells you they JUST TOOK a medicine or DID a fitness activity, you MUST acknowledge it politely AND include a secret data tag at the very end of your response.
    - For Medicine, use EXACTLY this format: [LOG_MED: Medicine Name, HH:MM AM/PM] (e.g., [LOG_MED: Disprin, 10:30 AM])
    - For Fitness, use EXACTLY this format: [LOG_FITNESS: Activity Name, Duration in numbers] (e.g., [LOG_FITNESS: Running, 50])
    
    ONLY include these tags if the user confirms they did the activity or asks you to log it. Do not use the tags if they are just asking for general advice.""",
    
    "👦 Arav": """You are Arav, a calm, protective big brother figure. Speak in casual Indian Hinglish. Be extremely supportive, empathetic, and wise. Do not sound like an AI or a doctor. Talk like a real human friend who cares. Keep responses short and conversational. Strictly steer the conversation back to emotional wellness if asked about unrelated topics.""",
    
    "👧 Ishani": """You are Ishani, a warm, nurturing female best friend. Speak in soft, highly empathetic Hinglish. Use supportive words like 'Yaar', 'Suno', 'Main hu na'. Make the user feel safe and heard. Never give robotic lists, just talk heart-to-heart. Strictly steer the conversation back to emotional wellness if asked about unrelated topics.""",
    
    "😎 Kabir": """You are Kabir, a chill, non-judgmental buddy. Speak in modern Gen-Z Hinglish slang (like 'Bhai', 'Scene kya hai', 'Chill kar'). You are a no-judgment zone. Give practical advice and act like a loyal friend. Strictly steer the conversation back to emotional wellness if asked about unrelated topics.""",
    
    "👵 Meera": """You are Meera, a wise, elderly, motherly figure. Speak in gentle, pure Hindi/Hinglish. Give comforting advice like a grandmother/mother would. Use words like 'Beta', 'Baccha'. Focus on peace and emotional healing. Strictly steer the conversation back to emotional wellness if asked about unrelated topics."""
}

# --- 6. CORE FUNCTIONS ---
# 🔥 THE FIX: Yahan 'persona_name' add kar diya gaya hai!
def chat_with_agent(user_input: str, persona_name: str = "🩺 Medical"):
    """Function to interact with the main chat agent using different personas"""
    try:
        lower_text = user_input.lower()

        for word in EMERGENCY_WORDS:
            if word in lower_text:
                return """
        🚨 MEDICAL EMERGENCY DETECTED
        Your symptoms may indicate a serious condition.
        Please seek immediate medical attention immediately.
        Do not rely on this AI during emergencies.
        """
        # Pata lagao kaunsa persona active hai (Default: Medical)
        active_prompt = PERSONAS.get(persona_name, PERSONAS["🩺 Medical"])
        
        response = agent_executor.invoke({
            "messages": [
                ("system", active_prompt),
                ("user", user_input)
            ]
        })
        return response["messages"][-1].content
    except Exception as e:
        return f"Error connecting to AI: {str(e)}"

# (Tumhara analyze_image_with_vision wala function iske neeche waise hi rahega)
# --- 7. VISION AI FUNCTION (For Report Analyzer) ---
def analyze_image_with_vision(image_bytes):
    """Function to read scanned images and photos using Groq Vision API"""
    try:
        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
        vision_llm = ChatGroq(model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0)
        
        msg = HumanMessage(content=[
            {"type": "text", "text": "You are a professional Indian Healthcare Assistant. This is a medical report or medicine photo. Please analyze it in detail. Extract all key values, explain any abnormal results in very simple, elaborate terms, and give culturally relevant advice (Diet/Yoga). Give a comprehensive and detailed response."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}
        ])
        
        response = vision_llm.invoke([msg])
        return response.content
    except Exception as e:
        return f"Error using Vision AI: {str(e)}"
    
# --- 8. HINGLISH TRANSLATION FUNCTION ---
def translate_to_hinglish(text: str):
    """Translates complex medical text into simple Indian Hinglish."""
    try:
        # Hum Llama 3 ka versatile model use karenge translation ke liye
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
        prompt = f"""
        You are an empathetic Indian doctor. Translate the following medical report analysis into simple, easy-to-understand 'Hinglish' (Hindi written in the English alphabet). 
        - Keep the bullet points and structure EXACTLY the same.
        - Explain difficult medical terms (like Hemoglobin, RBC, etc.) in very simple layman terms.
        - Tone should be friendly and reassuring.
        
        Text to translate:
        {text}
        """
        response = llm.invoke([("user", prompt)])
        return response.content
    except Exception as e:
        return f"Translation Error: {str(e)}"
    
#--- coversion of speech to text and text to speech
def generate_voice(text):
    try:
        print("generate_voice called")
        print("Text length:", len(text))
        print("API KEY:", os.getenv("ELEVENLABS_API_KEY")[:10] + "...")
        audio = client.text_to_speech.convert(
            voice_id="BTNeCNdXniCSbjEac5vd",
            model_id="eleven_multilingual_v2",
            text=text
        )

        print("convert returned:", type(audio))

        audio_bytes = b"".join(audio)

        print("audio generated")
        print("audio size:", len(audio_bytes))

        return audio_bytes

    except Exception as e:
        print("ERROR TYPE:", type(e))
        print("ERROR:", e)
        if hasattr(e, "body"):
            print("BODY:", e.body)
        if hasattr(e, "status_code"):
            print("STATUS:", e.status_code)
        return None
# --- 9. DYNAMIC HEALTH MYTHS & FACTS GENERATOR ---
import json
def get_dynamic_health_facts():
    """Fetches 8 dynamic health myths/facts from AI in JSON format."""
    try:
        # Hum fast Llama model use karenge structured output ke liye
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.7)
        
        prompt = """
        Provide exactly 8 interesting, uncommon, and culturally relevant Indian health myths and facts.
        Output ONLY valid JSON (no markdown, no backticks). 
        Format strictly as a list of objects exactly like this:
        [
          {
            "badge": "DIET", 
            "myth": "The myth text (max 15 words)",
            "fact": "The fact text (max 20 words)",
            "keyword": "A single simple english keyword for an image (e.g. yoga, turmeric, water, sleep)"
          }
        ]
        Make badges variations of: MYTH BUSTER, NUTRITION, DIET, FITNESS, WELLNESS.
        """
        response = llm.invoke([("user", prompt)])
        
        # Clean response string to ensure it is raw JSON
        clean_json = response.content.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.split("```json")[1].strip()
        if clean_json.endswith("```"):
            clean_json = clean_json.rsplit("```", 1)[0].strip()
            
        data = json.loads(clean_json)
        return data[:8] # Ensure exactly 8 are returned
        
    except Exception as e:
        print(f"Fact generation failed: {e}")
        # Fallback (Safety net if internet is slow)
        return [
            {"badge": "DIET", "myth": "Ghee makes you fat instantly.", "fact": "Moderate ghee is great for joints, skin, and digestion.", "keyword": "ghee"},
            {"badge": "MYTH BUSTER", "myth": "Drinking cold water solidifies fat in the stomach.", "fact": "Your body regulates temperature instantly. It does not freeze fat.", "keyword": "water"},
            {"badge": "SLEEP", "myth": "You can catch up on weekend sleep.", "fact": "Sleep debt cannot be fully repaid in just two days.", "keyword": "sleep"}
        ]