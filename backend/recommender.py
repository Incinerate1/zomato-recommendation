import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path=env_path)

# Initialize Groq client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

def get_groq_client():
    if not GROQ_API_KEY:
        return None
    try:
        return Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        print(f"Error initializing Groq client: {e}")
        return None

def generate_recommendations(candidates, preferences, extra_preferences=""):
    """
    Generate personalized recommendations from candidate restaurants based on preferences.
    """
    if not candidates:
        return []

    # If no Groq API Key, run fallback recommendation logic immediately
    client = get_groq_client()
    if not client:
        print("Warning: GROQ_API_KEY is not set. Using rule-based fallback recommendation.")
        return generate_fallback_recommendations(candidates, preferences, extra_preferences)

    # Prepare candidate data for prompt (minimize tokens by passing only relevant fields)
    prompt_candidates = []
    for c in candidates:
        prompt_candidates.append({
            "name": c["name"],
            "cuisines": c["cuisines"],
            "location": c["location"],
            "approx_cost": c["approx_cost"],
            "rate": c["rate"],
            "votes": c["votes"],
            "rest_type": c["rest_type"]
        })

    prompt = f"""
You are an AI-powered restaurant recommender assistant for Zomato.
Your task is to review the following candidate restaurants and recommend the top 3 that best match the user's requirements.

User Preferences:
- Location: {preferences.get('location')}
- Budget: {preferences.get('budget')}
- Cuisine: {preferences.get('cuisine')}
- Minimum Rating: {preferences.get('min_rating')}
- Extra Preferences/Context: {extra_preferences}

Candidate Restaurants from Database:
{json.dumps(prompt_candidates, indent=2)}

Instructions:
1. Rank and choose the top 3 restaurants that best match the user's structured preferences AND the extra preferences.
2. You MUST ONLY recommend restaurants that exist in the candidate list above. DO NOT invent or hallucinate any restaurant names.
3. For each recommended restaurant, write a personalized, engaging 2-sentence explanation of why this restaurant is a great match for their preferences (referencing their cuisine, budget, or extra preferences like vibe/service).
4. Output your response ONLY as a valid JSON object matching the schema below. Do not include any conversational preamble or postscript.

Output JSON Schema:
{{
  "recommendations": [
    {{
      "name": "Restaurant Name (MUST match name in candidates list exactly)",
      "rank": 1,
      "explanation": "A personalized 2-sentence explanation."
    }}
  ]
}}
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful and precise restaurant recommender assistant that outputs strict JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1000
        )
        
        response_text = chat_completion.choices[0].message.content
        return parse_llm_response(response_text, candidates)
        
    except Exception as e:
        print(f"Groq API error: {e}. Falling back to rule-based recommendations.")
        return generate_fallback_recommendations(candidates, preferences, extra_preferences)

def parse_llm_response(response_text, candidates):
    """
    Parses LLM response, extracts recommendations list, and validates names against candidates.
    """
    try:
        # Strip markdown code blocks if the model wrapped it in ```json ... ```
        clean_text = response_text.strip()
        if clean_text.startswith("```"):
            # Use regex to extract content inside code block
            match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
            if match:
                clean_text = match.group(1)
                
        data = json.loads(clean_text)
        recommendations = data.get("recommendations", [])
        
        # Build mapping of candidate name (lowercased) -> original candidate info
        candidate_map = {c["name"].lower().strip(): c for c in candidates}
        
        final_recs = []
        for rec in recommendations:
            name = rec.get("name", "").strip()
            rank = rec.get("rank")
            explanation = rec.get("explanation", "").strip()
            
            # Match check (case-insensitive) to prevent hallucinated restaurant names
            matched_candidate = candidate_map.get(name.lower())
            if matched_candidate:
                # Merge explanation and rank into the candidate's original details
                rec_details = dict(matched_candidate)
                rec_details["rank"] = rank
                rec_details["ai_explanation"] = explanation
                final_recs.append(rec_details)
                
        # If no recommendation matched, fall back
        if not final_recs:
            return generate_fallback_recommendations(candidates, {}, "")
            
        # Ensure they are sorted by rank
        final_recs.sort(key=lambda x: x.get("rank", 99))
        return final_recs
        
    except Exception as e:
        print(f"Error parsing LLM response: {e}. Raw response: {response_text}")
        return generate_fallback_recommendations(candidates, {}, "")

def generate_fallback_recommendations(candidates, preferences, extra_preferences):
    """
    Rule-based recommendation system fallback. Matches candidate restaurants and formats
    responses with templates.
    """
    # Select up to 3 candidates
    selected = candidates[:3]
    recs = []
    for idx, c in enumerate(selected):
        rank = idx + 1
        
        # Generate a fallback explanation based on the restaurant details
        cuisine_part = c.get('cuisines', 'great food')
        loc_part = c.get('location', 'the local area')
        rate_val = c.get('rate_float')
        cost_val = c.get('approx_cost')
        
        rate_str = f"rated {rate_val}/5" if rate_val else "highly recommended"
        cost_str = f"costs around {cost_val} for two" if cost_val else "is budget friendly"
        
        explanation = (
            f"Recommended because it is a popular spot in {loc_part} known for serving delicious {cuisine_part}. "
            f"It is {rate_str} and {cost_str}, matching your preferences perfectly."
        )
        
        rec_details = dict(c)
        rec_details["rank"] = rank
        rec_details["ai_explanation"] = explanation
        recs.append(rec_details)
        
    return recs


# ---------------------------------------------------------------------------
# Streaming variant — yields LLM tokens as they arrive
# ---------------------------------------------------------------------------

def _build_prompt(candidates, preferences, extra_preferences=""):
    """Build the LLM prompt (shared between normal and streaming paths)."""
    prompt_candidates = []
    for c in candidates:
        prompt_candidates.append({
            "name": c["name"],
            "cuisines": c["cuisines"],
            "location": c["location"],
            "approx_cost": c["approx_cost"],
            "rate": c["rate"],
            "votes": c["votes"],
            "rest_type": c["rest_type"]
        })

    return f"""
You are an AI-powered restaurant recommender assistant for Zomato.
Your task is to review the following candidate restaurants and recommend the top 3 that best match the user's requirements.

User Preferences:
- Location: {preferences.get('location')}
- Budget: {preferences.get('budget')}
- Cuisine: {preferences.get('cuisine')}
- Minimum Rating: {preferences.get('min_rating')}
- Extra Preferences/Context: {extra_preferences}

Candidate Restaurants from Database:
{json.dumps(prompt_candidates, indent=2)}

Instructions:
1. Rank and choose the top 3 restaurants that best match the user's structured preferences AND the extra preferences.
2. You MUST ONLY recommend restaurants that exist in the candidate list above. DO NOT invent or hallucinate any restaurant names.
3. For each recommended restaurant, write a personalized, engaging 2-sentence explanation of why this restaurant is a great match for their preferences (referencing their cuisine, budget, or extra preferences like vibe/service).
4. Output your response ONLY as a valid JSON object matching the schema below. Do not include any conversational preamble or postscript.

Output JSON Schema:
{{
  "recommendations": [
    {{
      "name": "Restaurant Name (MUST match name in candidates list exactly)",
      "rank": 1,
      "explanation": "A personalized 2-sentence explanation."
    }}
  ]
}}
"""


async def generate_recommendations_stream(candidates, preferences, extra_preferences=""):
    """
    Async generator that yields LLM response tokens as they arrive.
    Used by the SSE streaming endpoint.
    """
    if not candidates:
        return

    client = get_groq_client()
    if not client:
        # Fallback: yield the full fallback JSON at once
        fallback = generate_fallback_recommendations(candidates, preferences, extra_preferences)
        yield json.dumps({"recommendations": [
            {"name": r["name"], "rank": r["rank"], "explanation": r["ai_explanation"]}
            for r in fallback
        ]})
        return

    prompt = _build_prompt(candidates, preferences, extra_preferences)

    try:
        stream = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful and precise restaurant recommender assistant that outputs strict JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=1000,
            stream=True
        )

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    except Exception as e:
        # On streaming failure, yield the fallback as a complete JSON string
        print(f"Groq streaming error: {e}. Yielding fallback.")
        fallback = generate_fallback_recommendations(candidates, preferences, extra_preferences)
        yield json.dumps({"recommendations": [
            {"name": r["name"], "rank": r["rank"], "explanation": r["ai_explanation"]}
            for r in fallback
        ]})
