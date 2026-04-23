import json
import logging
from datetime import datetime
from typing import List

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError

from .models import PersonalityProfile

logger = logging.getLogger(__name__)


class Stage1Signals(BaseModel):
    avg_sentence_length: float = Field(..., ge=0)
    sentence_length_variance: float = Field(..., ge=0)
    vocabulary_richness: float = Field(..., ge=0, le=1)
    pronoun_i_count: int = Field(..., ge=0)
    pronoun_we_count: int = Field(..., ge=0)
    hedging_density: float = Field(..., ge=0, le=1)
    active_voice_ratio: float = Field(..., ge=0, le=1)
    passive_voice_ratio: float = Field(..., ge=0, le=1)
    emotional_vocabulary_density: float = Field(..., ge=0, le=1)
    positive_emotion_ratio: float = Field(..., ge=0, le=1)
    negative_emotion_ratio: float = Field(..., ge=0, le=1)
    sentence_rhythm_score: float = Field(..., ge=0, le=1)
    notable_liwc_style_cues: List[str]


class Stage2Traits(BaseModel):
    openness: float = Field(..., ge=0, le=1)
    conscientiousness: float = Field(..., ge=0, le=1)
    extraversion: float = Field(..., ge=0, le=1)
    agreeableness: float = Field(..., ge=0, le=1)
    neuroticism: float = Field(..., ge=0, le=1)
    openness_confidence: float = Field(..., ge=0, le=1)
    conscientiousness_confidence: float = Field(..., ge=0, le=1)
    extraversion_confidence: float = Field(..., ge=0, le=1)
    agreeableness_confidence: float = Field(..., ge=0, le=1)
    neuroticism_confidence: float = Field(..., ge=0, le=1)
    dominant_trait: str


class Stage4Narrative(BaseModel):
    tone_analysis: str
    writing_style: str
    summary: str


def _derive_mbti_from_big_five(traits: Stage2Traits) -> str:
    """
    Deterministic MBTI approximation from Big Five with commonly used mappings:
    E/I <- Extraversion
    N/S <- Openness
    F/T <- Agreeableness (higher A leans F)
    J/P <- Conscientiousness
    """
    e_or_i = "E" if traits.extraversion >= 0.5 else "I"
    n_or_s = "N" if traits.openness >= 0.5 else "S"
    f_or_t = "F" if traits.agreeableness >= 0.5 else "T"
    j_or_p = "J" if traits.conscientiousness >= 0.5 else "P"
    return f"{e_or_i}{n_or_s}{f_or_t}{j_or_p}"


def _analysis_quality_from_confidence(confidence_score: int) -> str:
    if confidence_score >= 80:
        return "High"
    if confidence_score >= 55:
        return "Medium"
    return "Low"


def _unwrap_json_block(text: str) -> str:
    clean_text = (text or "").strip()
    if "</scratchpad>" in clean_text:
        clean_text = clean_text.split("</scratchpad>")[-1].strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    return clean_text.strip()


async def _call_json_with_retry(model, prompt: str, schema_model):
    """Call Gemini and parse strict JSON with one retry using a stricter instruction."""
    for attempt in range(2):
        response = await model.generate_content_async(prompt)
        raw_text = _unwrap_json_block(response.text)
        try:
            data = json.loads(raw_text)
            return schema_model(**data)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.warning("Stage parsing failed on attempt %s: %s", attempt + 1, exc)
            if attempt == 0:
                prompt = (
                    prompt
                    + "\n\nCRITICAL RETRY INSTRUCTION: Output only strict JSON."
                    + " No markdown, no commentary, no prose, no extra keys."
                )
    return None

async def analyze_personality(text, config=None):
    """
    Analyze personality traits from text input using a multi-stage Gemini pipeline.
    """
    
    # Basic validation
    if not text or len(text.strip()) < 10:
        return {
            "success": False,
            "error": "Text too short for analysis. Please provide at least 10 characters.",
            "timestamp": datetime.now().isoformat()
        }
        
    try:
        if config and hasattr(config, "gemini_api_key") and config.gemini_api_key:
            genai.configure(api_key=config.gemini_api_key)
            
        model = genai.GenerativeModel("gemini-1.5-pro")

        # Stage 1: Extract LIWC-style linguistic signals.
        stage1_prompt = f"""You are conducting psycholinguistic feature extraction.
Use validated Big Five (OCEAN) psycholinguistic framing and LIWC-style cues.

Analyze this text for:
- Pronoun use (I/me/my vs we/us/our)
- Hedging language density
- Active vs passive voice
- Emotional vocabulary density and polarity
- Sentence rhythm (length variation and cadence)

<scratchpad>
Reason through signals internally.
</scratchpad>

Return ONLY strict JSON with this exact schema and keys:
{{
  "avg_sentence_length": float,
  "sentence_length_variance": float,
  "vocabulary_richness": float,
  "pronoun_i_count": int,
  "pronoun_we_count": int,
  "hedging_density": float,
  "active_voice_ratio": float,
  "passive_voice_ratio": float,
  "emotional_vocabulary_density": float,
  "positive_emotion_ratio": float,
  "negative_emotion_ratio": float,
  "sentence_rhythm_score": float,
  "notable_liwc_style_cues": [string]
}}

Text:
{text}
"""
        stage1 = await _call_json_with_retry(model, stage1_prompt, Stage1Signals)
        if not stage1:
            raise ValueError("Failed to parse stage 1 signals.")

        # Stage 2: Map extracted signals to Big Five + per-trait confidence.
        stage2_prompt = f"""You are mapping psycholinguistic signals to Big Five traits.
Use conservative, research-grounded scoring.

Signals JSON:
{stage1.model_dump_json()}

<scratchpad>
Reason internally using LIWC-style evidence and cue reliability.
</scratchpad>

Return ONLY strict JSON with this exact schema and keys:
{{
  "openness": float,
  "conscientiousness": float,
  "extraversion": float,
  "agreeableness": float,
  "neuroticism": float,
  "openness_confidence": float,
  "conscientiousness_confidence": float,
  "extraversion_confidence": float,
  "agreeableness_confidence": float,
  "neuroticism_confidence": float,
  "dominant_trait": string
}}
"""
        stage2 = await _call_json_with_retry(model, stage2_prompt, Stage2Traits)
        if not stage2:
            raise ValueError("Failed to parse stage 2 trait mapping.")

        # Stage 3: Derive MBTI deterministically from Big Five.
        mbti_type = _derive_mbti_from_big_five(stage2)

        # Stage 4: Generate concise narrative outputs.
        stage4_prompt = f"""You are writing a personality narrative from validated trait estimates.

Big Five JSON:
{stage2.model_dump_json()}

Derived MBTI:
{mbti_type}

<scratchpad>
Reason internally about tone and style constraints.
</scratchpad>

Return ONLY strict JSON with this exact schema and keys:
{{
  "tone_analysis": string,
  "writing_style": string,
  "summary": string
}}

Constraints:
- tone_analysis: 2 sentences max
- writing_style: 2 sentences max
- summary: 3-4 sentences, warm and insightful
"""
        stage4 = await _call_json_with_retry(model, stage4_prompt, Stage4Narrative)
        if not stage4:
            raise ValueError("Failed to parse stage 4 narrative.")

        confidence_score = int(round(
            (
                stage2.openness_confidence
                + stage2.conscientiousness_confidence
                + stage2.extraversion_confidence
                + stage2.agreeableness_confidence
                + stage2.neuroticism_confidence
            )
            / 5
            * 100
        ))
        confidence_score = max(0, min(100, confidence_score))

        profile_data = PersonalityProfile(
            openness=stage2.openness,
            conscientiousness=stage2.conscientiousness,
            extraversion=stage2.extraversion,
            agreeableness=stage2.agreeableness,
            neuroticism=stage2.neuroticism,
            mbti_type=mbti_type,
            dominant_trait=stage2.dominant_trait,
            tone_analysis=stage4.tone_analysis,
            writing_style=stage4.writing_style,
            summary=stage4.summary,
            confidence_score=confidence_score,
            analysis_quality=_analysis_quality_from_confidence(confidence_score),
        )
            
        return {
            "success": True,
            "response": profile_data.model_dump(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        return {
            "success": False,
            "error": "Internal AI processing error.",
            "timestamp": datetime.now().isoformat()
        }

def _parse_and_validate(text: str) -> PersonalityProfile:
    try:
        clean_text = _unwrap_json_block(text)
        data = json.loads(clean_text)
        return PersonalityProfile(**data)
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Validation failed: {e}")
        return None
