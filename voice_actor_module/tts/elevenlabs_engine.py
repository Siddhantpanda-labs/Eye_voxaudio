import os
import requests

class ElevenLabsEngine:
    """
    Professional ElevenLabs TTS engine with full voice tuning control.
    
    Voice Settings Guide:
      stability       (0.0-1.0): Lower = more expressive/emotional, Higher = more consistent/robotic
      similarity      (0.0-1.0): How closely to match the original voice. Higher = closer match
      style           (0.0-1.0): Style exaggeration. Higher = more dramatic/cinematic delivery
      speaker_boost   (bool):    Enhances speaker clarity. Costs more latency but sounds better
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("ELEVENLABS_API_KEY")
        self.base_url = "https://api.elevenlabs.io/v1"
        
    def generate_audio(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        stability: float = 0.5,
        similarity: float = 0.75,
        style: float = 0.0,
        speaker_boost: bool = True,
    ):
        if not self.api_key:
            raise ValueError("ElevenLabs API key is missing.")
            
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity,
                "style": style,
                "use_speaker_boost": speaker_boost,
            }
        }
        
        print(f"Calling ElevenLabs API...")
        print(f"  Voice Settings: stability={stability}, similarity={similarity}, style={style}, boost={speaker_boost}")
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
            print(f"Audio saved to {output_path}")
            return output_path
        else:
            raise RuntimeError(f"API Error: {response.status_code} - {response.text}")
