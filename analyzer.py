import random
from datetime import datetime

async def analyze_personality(text, config=None):
    """
    Analyze personality traits from text input.
    This is a simplified version that provides varied responses.
    """
    
    # Basic validation
    if not text or len(text.strip()) < 10:
        return {
            "success": False,
            "error": "Text too short for analysis. Please provide at least 10 characters.",
            "timestamp": datetime.now().isoformat()
        }
    
    # Simple text-based analysis (placeholder for AI integration)
    text_lower = text.lower()
    text_length = len(text)
    
    # Generate varied personality scores based on text characteristics
    openness = min(0.9, max(0.1, 0.5 + (text.count('creative') + text.count('new') + text.count('idea')) * 0.1 + random.uniform(-0.2, 0.2)))
    conscientiousness = min(0.9, max(0.1, 0.5 + (text.count('plan') + text.count('organize') + text.count('goal')) * 0.1 + random.uniform(-0.2, 0.2)))
    extraversion = min(0.9, max(0.1, 0.5 + (text.count('people') + text.count('social') + text.count('party')) * 0.1 + random.uniform(-0.2, 0.2)))
    agreeableness = min(0.9, max(0.1, 0.5 + (text.count('help') + text.count('kind') + text.count('friend')) * 0.1 + random.uniform(-0.2, 0.2)))
    neuroticism = min(0.9, max(0.1, 0.5 + (text.count('worry') + text.count('stress') + text.count('anxious')) * 0.1 + random.uniform(-0.2, 0.2)))
    
    # Determine MBTI type based on scores
    mbti_types = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", 
                  "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"]
    
    # Simple MBTI determination
    e_or_i = "E" if extraversion > 0.5 else "I"
    s_or_n = "N" if openness > 0.5 else "S"
    t_or_f = "F" if agreeableness > 0.5 else "T"
    j_or_p = "J" if conscientiousness > 0.5 else "P"
    mbti_type = e_or_i + s_or_n + t_or_f + j_or_p
    
    # Generate tone analysis
    if "!" in text or text.isupper():
        tone = "energetic and expressive"
    elif "?" in text:
        tone = "curious and inquisitive"
    elif any(word in text_lower for word in ["love", "happy", "great", "amazing"]):
        tone = "positive and optimistic"
    elif any(word in text_lower for word in ["sad", "difficult", "problem", "worry"]):
        tone = "reflective and concerned"
    else:
        tone = "thoughtful and balanced"
    
    # Generate writing style analysis
    if text_length > 200:
        writing_style = "detailed and expressive"
    elif text_length < 50:
        writing_style = "concise and direct"
    else:
        writing_style = "balanced and clear"
    
    # Generate summary
    dominant_trait = max([
        ("openness", openness),
        ("conscientiousness", conscientiousness),
        ("extraversion", extraversion),
        ("agreeableness", agreeableness)
    ], key=lambda x: x[1])[0]
    
    summary = f"This person shows strong {dominant_trait} traits with a {tone.split(' and ')[0]} communication style."
    
    return {
        "success": True,
        "response": {
            "openness": round(openness, 2),
            "conscientiousness": round(conscientiousness, 2),
            "extraversion": round(extraversion, 2),
            "agreeableness": round(agreeableness, 2),
            "neuroticism": round(neuroticism, 2),
            "mbti_type": mbti_type,
            "tone_analysis": tone,
            "writing_style": writing_style,
            "summary": summary
        },
        "timestamp": datetime.now().isoformat()
    }
