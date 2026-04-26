import os
import re
import torch
import torchaudio
import numpy as np
from pathlib import Path
from chatterbox.tts import ChatterboxTTS
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

# Force use of local project directory for models
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "huggingface"))
os.environ["HF_HOME"] = MODELS_DIR

# Chatterbox's hardcoded max_new_tokens=1000 allows ~10-15s of speech.
# We chunk text at sentence boundaries to stay safely within that limit.
MAX_CHARS_PER_CHUNK = 220

def _split_into_chunks(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    """
    Splits text into sentence-level chunks under max_chars.
    Preserves ellipsis (...) — only splits on true sentence-ending punctuation
    that is NOT part of a '...' sequence.
    """
    # Split on: a single . ! or ? (not preceded by another . and not followed by another .)
    # followed by whitespace. This correctly leaves ... intact.
    sentences = re.split(r'(?<!\.)([.!?])(?!\.)(?=\s)', text.strip())
    
    # re.split with a capturing group gives: [text, delim, text, delim, ...]
    # Rebuild full sentences by pairing text with its delimiter
    rebuilt = []
    i = 0
    parts = re.split(r'(?<!\.)([.!?])(?!\.)(?=\s)', text.strip())
    i = 0
    while i < len(parts):
        chunk = parts[i]
        if i + 1 < len(parts) and parts[i + 1] in '.!?':
            chunk += parts[i + 1]
            i += 2
        else:
            i += 1
        if chunk.strip():
            rebuilt.append(chunk.strip())

    # Now group rebuilt sentences into max_chars buckets
    chunks = []
    current = ""
    for sentence in rebuilt:
        if current and len(current) + 1 + len(sentence) > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text]


class ChatterboxEngine:
    _instance = None       # Base model singleton
    _mtl_instance = None   # Multilingual model singleton
    _cached_conds = {}     # Cache: {cache_key: conditionals}

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

    def _generate_chunk(self, model, chunk: str, gen_kwargs: dict, exaggeration, cfg_weight, temperature, repetition_penalty, top_p, min_p) -> np.ndarray:
        """Generates audio for a single text chunk and returns raw numpy array."""
        wav = model.generate(
            chunk,
            exaggeration=exaggeration,
            cfg_weight=cfg_weight,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
            top_p=top_p,
            min_p=min_p,
            **gen_kwargs
        )
        if wav.ndim == 2:
            wav = wav.squeeze(0)
        return wav.cpu().numpy()

    def generate_audio(
        self,
        text: str,
        output_path: str,
        audio_prompt_path: str = None,
        language: str = "english",
        exaggeration: float = 0.5,
        cfg_weight: float = 0.5,
        temperature: float = 0.8,
        repetition_penalty: float = 1.5,
        top_p: float = 1.0,
        min_p: float = 0.05,
    ):
        """
        Generates audio using Chatterbox.
        Splits long texts into sentence chunks to bypass the library's
        hardcoded max_new_tokens=1000 limit, then concatenates the results.
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
            if audio_prompt_path and os.path.exists(audio_prompt_path):
                cache_key = f"{audio_prompt_path}:{exaggeration}"
                if cache_key not in ChatterboxEngine._cached_conds:
                    print(f"Processing voice profile from: {audio_prompt_path} (exaggeration={exaggeration})")
                    model.prepare_conditionals(audio_prompt_path, exaggeration=exaggeration)
                    ChatterboxEngine._cached_conds[cache_key] = model.conds
                    if len(ChatterboxEngine._cached_conds) > 3:
                        oldest = next(iter(ChatterboxEngine._cached_conds))
                        del ChatterboxEngine._cached_conds[oldest]
                else:
                    print(f"Using cached voice profile for: {audio_prompt_path}")
                    model.conds = ChatterboxEngine._cached_conds[cache_key]

            # --- Chunked Generation ---
            chunks = _split_into_chunks(text)
            print(f"Chatterbox generating {len(chunks)} chunk(s) for {len(text)} chars of text...")

            audio_parts = []
            silence = np.zeros(int(model.sr * 0.15), dtype=np.float32)  # 150ms silence between chunks

            for i, chunk in enumerate(chunks):
                print(f"  Chunk {i+1}/{len(chunks)}: '{chunk[:60]}{'...' if len(chunk) > 60 else ''}'")
                chunk_wav = self._generate_chunk(
                    model, chunk, gen_kwargs,
                    exaggeration, cfg_weight, temperature, repetition_penalty, top_p, min_p
                )
                audio_parts.append(chunk_wav)
                if i < len(chunks) - 1:
                    audio_parts.append(silence)  # Add brief pause between sentences

            # Concatenate all chunks into one continuous audio
            final_wav = np.concatenate(audio_parts)
            wav_tensor = torch.from_numpy(final_wav).unsqueeze(0)

            torchaudio.save(output_path, wav_tensor, model.sr)
            print(f"✅ Audio saved to {output_path} ({len(chunks)} chunk(s), {len(final_wav)/model.sr:.1f}s)")
            return output_path

        except Exception as e:
            print(f"❌ Chatterbox generation failed: {e}")
            raise e
