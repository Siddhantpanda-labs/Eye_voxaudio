import os
import torch
import torchaudio
from pathlib import Path
from chatterbox.tts import ChatterboxTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

# Force use of local project directory for models
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "huggingface"))
os.environ["HF_HOME"] = MODELS_DIR

class ChatterboxEngine:
    _instance = None       # Base model singleton
    _mtl_instance = None   # Multilingual model singleton
    _cached_conds = {}     # Cache: {ref_audio_path: conditionals}

    def __init__(self, device=None):
        if device is None:
            if torch.cuda.is_available():
                self.device = "cuda"
            elif torch.backends.mps.is_available():
                self.device = "mps"
            else:
                self.device = "cpu"
        else:
            self.device = device

    def _get_base_model(self):
        # Evict multilingual from VRAM first if loaded
        if ChatterboxEngine._mtl_instance is not None:
            print("Evicting Multilingual model from VRAM to free memory...")
            del ChatterboxEngine._mtl_instance
            ChatterboxEngine._mtl_instance = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if ChatterboxEngine._instance is None:
            print(f"Loading Chatterbox Turbo (Base) on {self.device}...")
            ChatterboxEngine._instance = ChatterboxTTS.from_pretrained(device=self.device)
            print("✅ Chatterbox Base ready.")
        return ChatterboxEngine._instance

    def _get_mtl_model(self):
        # Evict base from VRAM first if loaded
        if ChatterboxEngine._instance is not None:
            print("Evicting Base model from VRAM to free memory...")
            del ChatterboxEngine._instance
            ChatterboxEngine._instance = None
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

        if ChatterboxEngine._mtl_instance is None:
            print(f"Loading Chatterbox Multilingual on {self.device}...")
            ChatterboxEngine._mtl_instance = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            print("✅ Chatterbox Multilingual ready.")
        return ChatterboxEngine._mtl_instance

    def generate_audio(
        self,
        text: str,
        output_path: str,
        audio_prompt_path: str = None,
        language: str = "english",
        # --- Chatterbox Advanced Parameters ---
        exaggeration: float = 0.5,       # Emotion intensity: 0=flat, 1=very expressive
        cfg_weight: float = 0.5,         # Clone fidelity: 0=creative, 1=exact clone
        temperature: float = 0.8,        # Spontaneity: 0.1=robotic, 1.5=very human
        repetition_penalty: float = 1.2, # Loop guard: prevents unnatural repetitions
        top_p: float = 1.0,              # Vocab breadth: nucleus sampling
        min_p: float = 0.05,             # Precision: minimum token probability
    ):
        """
        Generates audio using Chatterbox.
        Automatically switches between Base and Multilingual models based on language.
        Caches voice conditionals so the reference audio is only processed once.
        """
        try:
            lang_map = {
                "hindi": "hi", "hinglish": "hi",
                "french": "fr", "german": "de",
                "spanish": "es", "japanese": "ja",
                "chinese": "zh"
            }
            lang_id = lang_map.get(language.lower(), None)

            if lang_id:
                print(f"Using Multilingual model for language: {language} ({lang_id})")
                model = self._get_mtl_model()
                gen_kwargs = {"language_id": lang_id}
            else:
                print(f"Using Base model for language: {language}")
                model = self._get_base_model()
                gen_kwargs = {}

            # --- Pre-baked Conditionals Cache ---
            # Process reference audio once and reuse for subsequent generates
            if audio_prompt_path and os.path.exists(audio_prompt_path):
                cache_key = f"{audio_prompt_path}:{exaggeration}"
                if cache_key not in ChatterboxEngine._cached_conds:
                    print(f"Processing voice profile from: {audio_prompt_path} (exaggeration={exaggeration})")
                    model.prepare_conditionals(audio_prompt_path, exaggeration=exaggeration)
                    ChatterboxEngine._cached_conds[cache_key] = model.conds
                    # Limit cache to last 3 profiles to avoid memory bloat
                    if len(ChatterboxEngine._cached_conds) > 3:
                        oldest = next(iter(ChatterboxEngine._cached_conds))
                        del ChatterboxEngine._cached_conds[oldest]
                else:
                    print(f"Using cached voice profile for: {audio_prompt_path}")
                    model.conds = ChatterboxEngine._cached_conds[cache_key]

                wav = model.generate(
                    text,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature,
                    repetition_penalty=repetition_penalty,
                    top_p=top_p,
                    min_p=min_p,
                    **gen_kwargs
                )
            else:
                wav = model.generate(
                    text,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight,
                    temperature=temperature,
                    repetition_penalty=repetition_penalty,
                    top_p=top_p,
                    min_p=min_p,
                    **gen_kwargs
                )

            if wav.ndim == 1:
                wav = wav.unsqueeze(0)

            torchaudio.save(output_path, wav.cpu(), model.sr)
            print(f"✅ Audio saved to {output_path}")
            return output_path

        except Exception as e:
            print(f"❌ Chatterbox generation failed: {e}")
            raise e
