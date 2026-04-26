import re

# The EXACT tokens supported by the Chatterbox tokenizer (sourced from tokenizer.json).
# These are the ONLY tokens that produce sounds. Anything else is spoken as text.
CHATTERBOX_VALID_TOKENS = {
    "[uh]", "[um]",
    "[giggle]", "[laughter]", "[guffaw]",
    "[inhale]", "[exhale]", "[sigh]",
    "[cry]", "[gasp]", "[groan]",
    "[whisper]", "[mumble]",
    "[sniff]", "[sneeze]", "[cough]", "[snore]",
    "[chew]", "[sip]", "[clear_throat]",
    "[kiss]", "[shhh]", "[gibberish]",
    "[singing]", "[music]", "[whistle]", "[humming]",
}

class TextTransformer:
    def condition_text(self, original_text: str, intent: dict, engine: str = "elevenlabs") -> str:
        """
        Transforms structured intent into TTS-friendly expressive input.
        
        For Chatterbox: strips all non-whitelisted bracket tokens so the engine
        never tries to speak instruction text like '[calm tone, narration]'.
        For other engines: prepends the emotion/style header as before.
        """
        refined_text = intent.get("refined_text", original_text)

        if engine == "chatterbox":
            # Strip any bracket tokens that aren't in the valid Chatterbox whitelist.
            # This removes things like [calm tone, narration] while keeping [laugh], [sigh] etc.
            def keep_valid_tokens(match):
                token = match.group(0).lower()
                return token if token in CHATTERBOX_VALID_TOKENS else ""

            cleaned = re.sub(r'\[[^\]]+\]', keep_valid_tokens, refined_text)
            # Collapse any double spaces left behind after removing tokens
            cleaned = re.sub(r'  +', ' ', cleaned).strip()
            return cleaned

        # For cloud engines (ElevenLabs etc.), keep the metadata header
        emotion = intent.get("emotion", "calm")
        style = intent.get("style", "narration")
        return f"[{emotion} tone, {style}] {refined_text}"
