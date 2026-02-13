import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

def translate_content(text):
    """Translates text to Korean using Gemini API."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY not found in environment variables.")
        return text + " (번역 실패: API Key 없음)"

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        Translate the following AI news content to natural, professional Korean.
        If it's a title, keep it concise. If it's a summary, make it easy to understand.
        
        Content:
        {text}
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        return text + " (번역 실패: 오류 발생)"
