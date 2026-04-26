import os
import json
import requests

class IntentParser:
    def __init__(self, use_llm=True, api_key=None):
        self.use_llm = use_llm
        self.api_key = api_key
        
        if self.use_llm and not self.api_key:
            self.api_key = self._get_openai_key()

    def _get_openai_key(self):
        key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chatgpt.key.txt")
        if os.path.exists(key_path):
            with open(key_path, 'r') as f:
                return f.read().strip()
        return os.environ.get("OPENAI_API_KEY")

    def parse_intent(self, text: str, engine: str = "elevenlabs", requested_tone: str = "auto", hesitation: int = 0, breathiness: int = 0) -> dict:
        if self.use_llm and self.api_key:
            return self._parse_with_llm(text, engine, requested_tone, hesitation, breathiness)
        else:
            print("Warning: LLM API key not found, falling back to rules.")
            return self._parse_with_rules(text)

    def _parse_with_llm(self, text: str, engine: str, requested_tone: str, hesitation: int, breathiness: int) -> dict:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        tag_instruction = 'Use square brackets for directions like "[laughter]" or "[sigh]".'
        if engine == "chatterbox":
            tag_instruction = 'You MUST use specific Chatterbox paralinguistic tags: "[laugh]", "[sigh]", "[cough]", "[chuckle]", "[gasp]". Use these sparingly to enhance the dialogue.'

        tone_instruction = "Infer the most appropriate emotion and style based on the text."
        if requested_tone.lower() != "auto":
            tone_instruction = f"The user has EXPLICITLY REQUESTED the tone/feel to be: '{requested_tone}'. You MUST adapt the performance and text refinement to match this exact tone, even if the text normally wouldn't sound like it."

        director_notes = []
        if hesitation > 0:
            if hesitation > 50:
                director_notes.append(f"HIGH HESITATION ({hesitation}/100): The character is extremely unsure, anxious, or stammering. Add frequent stutters (e.g., 'I... I-I don't know'), cut-off words with dashes ('stop-'), and filler words ('um', 'uh').")
            else:
                director_notes.append(f"MILD HESITATION ({hesitation}/100): Add occasional slight pauses or minor stutters.")
                
        if breathiness > 0:
            if breathiness > 50:
                director_notes.append(f"HIGH BREATHINESS ({breathiness}/100): The character is exhausted, terrified, or speaking very closely. Add frequent literal [breath] or [sigh] tags, and use ellipses (...) for breathy pauses.")
            else:
                director_notes.append(f"MILD BREATHINESS ({breathiness}/100): Add occasional [breath] tags or slight pauses.")

        director_text = ""
        if director_notes:
            director_text = "\n\nCRITICAL DIRECTOR'S NOTES FOR TEXT REFINEMENT:\n- " + "\n- ".join(director_notes)

        system_prompt = f"""You are an expert AI voice acting director and script supervisor. 
Your job is to analyze the user's text and output optimal vocal delivery parameters.

Crucially, you must also REFINE the text for the voice actor (TTS).
- {tag_instruction}
- Example: (laughs) -> "[laugh]" (if chatterbox) or "[laughter]" (otherwise)
- Example: (shouts) -> CONVERT THE FOLLOWING TEXT TO ALL CAPS.
- Add dramatic pauses using '...' where appropriate.
- Add commas for natural breathing.
- If the text is in Hinglish (Hindi written in English) or pure Hindi, ensure the spelling and punctuation guide the TTS to pronounce it with a natural Indian/Hindi accent. Feel free to tweak spelling to ensure the TTS reads the Hindi correctly.
- Do NOT use parentheses ( ) for sounds; use [ ] instead.
- Do NOT completely change the core meaning, just enhance the pacing and delivery.{director_text}

{tone_instruction}

Output ONLY valid JSON matching this schema:
{{
  "emotion": "detected or requested emotion",
  "intensity": 0.0 to 1.0,
  "pacing": 0.5 to 1.5,
  "style": "whisper | narration | dramatic | conversational | shouting",
  "language": "english | hinglish | hindi",
  "refined_text": "The enhanced script with pauses, expression tags, and optimal TTS formatting"
}}"""

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4
        }

        try:
            print(f"Calling OpenAI API for {engine} intent and refinement...")
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            print(f"LLM parsing failed: {e}")
            return self._parse_with_rules(text)

    def _parse_with_rules(self, text: str) -> dict:
        return {
            "emotion": "calm",
            "intensity": 0.5,
            "pacing": 1.0,
            "style": "narration",
            "language": "english",
            "refined_text": text
        }
