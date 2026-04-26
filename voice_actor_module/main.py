import os
import argparse
from intent.intent_parser import IntentParser
from conditioning.text_transform import TextTransformer
from tts.elevenlabs_engine import ElevenLabsEngine
from fx.audio_fx import AudioFX

def get_elevenlabs_key():
    # Assuming key is in the project root
    key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elevenlabs.key.txt")
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip()
    return os.environ.get("ELEVENLABS_API_KEY")

def main():
    parser = argparse.ArgumentParser(description="AI Voice Acting System (ElevenLabs Mode)")
    parser.add_argument("--text", type=str, required=True, help="Text to synthesize")
    parser.add_argument("--voice_id", type=str, default="pNInz6obpgDQGcFmaJgB", help="ElevenLabs Voice ID (default: Adam)")
    parser.add_argument("--output", type=str, default="output.wav", help="Output file path")
    parser.add_argument("--apply_fx", action="store_true", help="Apply post-processing effects")
    args = parser.parse_args()

    print("--- AI Voice Acting System ---")
    
    api_key = get_elevenlabs_key()
    if not api_key:
        print("Error: ElevenLabs API key not found in elevenlabs.key.txt or ELEVENLABS_API_KEY env var.")
        return

    # 1. Intent Parsing
    print("\n[1] Parsing Intent...")
    intent_parser = IntentParser()
    intent = intent_parser.parse_intent(args.text)
    print(f"Detected Intent: {intent}")
    
    # 2. Text Conditioning
    print("\n[2] Conditioning Text...")
    transformer = TextTransformer()
    conditioned_text = transformer.condition_text(args.text, intent)
    print(f"Conditioned Text: {conditioned_text}")
    
    # 3. Voice Synthesis (ElevenLabs API)
    print("\n[3] Synthesizing Voice (ElevenLabs)...")
    raw_output = "raw_" + args.output
    tts_engine = ElevenLabsEngine(api_key=api_key)
    try:
        tts_engine.generate_audio(
            text=conditioned_text,
            voice_id=args.voice_id,
            output_path=raw_output
        )
    except Exception as e:
        print(f"TTS Synthesis failed: {e}")
        return

    # 4. Audio Post-Processing
    if args.apply_fx:
        print("\n[4] Applying Audio FX...")
        fx = AudioFX()
        try:
            fx.apply_effects(input_path=raw_output, output_path=args.output)
            print(f"\nFinal output available at: {args.output}")
            if os.path.exists(raw_output):
                os.remove(raw_output)
        except Exception as e:
            print(f"Audio FX failed: {e}")
    else:
        # Rename raw output to final output
        if os.path.exists(args.output):
            os.remove(args.output)
        os.rename(raw_output, args.output)
        print(f"\nFinal output available at: {args.output}")

if __name__ == "__main__":
    main()
