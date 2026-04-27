import os
import time
import uuid
import uvicorn
from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from intent.intent_parser import IntentParser
from conditioning.text_transform import TextTransformer
from tts.elevenlabs_engine import ElevenLabsEngine
from fx.audio_fx import AudioFX
import requests as http_requests
import json

app = FastAPI()

static_dir = os.path.join(os.path.dirname(__file__), "static")
output_dir = os.path.join(static_dir, "outputs")
os.makedirs(output_dir, exist_ok=True)

VOICES_DIR = os.path.join(os.path.dirname(__file__), "voices")
os.makedirs(VOICES_DIR, exist_ok=True)
VOICES_JSON = os.path.join(VOICES_DIR, "voices.json")

def get_cb_voices():
    if not os.path.exists(VOICES_JSON):
        return []
    with open(VOICES_JSON, "r") as f:
        return json.load(f)

def save_cb_voices(voices):
    with open(VOICES_JSON, "w") as f:
        json.dump(voices, f, indent=4)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

class SynthesisRequest(BaseModel):
    text: str
    voice_id: str
    tone: str = "auto"
    apply_fx: bool = False
    hesitation: int = 0
    breathiness: int = 0

from typing import List

class ConvLine(BaseModel):
    text: str
    engine: str
    voice_id: str
    target_language: str

class ConvRequest(BaseModel):
    lines: List[ConvLine]
    apply_fx: bool = False

def get_elevenlabs_key():
    key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "elevenlabs.key.txt")
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            return f.read().strip()
    return os.environ.get("ELEVENLABS_API_KEY")

@app.get("/")
def read_root():
    return FileResponse(os.path.join(static_dir, "index.html"))

def convert_to_mp3(wav_path: str, mp3_path: str):
    import subprocess
    import shutil
    ffmpeg_cmd = r"D:\Program Files\ThirdParty\ffmpeg\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_cmd):
        ffmpeg_cmd = shutil.which("ffmpeg") or "ffmpeg"
    subprocess.run([ffmpeg_cmd, "-y", "-i", wav_path, "-b:a", "192k", mp3_path], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

@app.get("/api/voices")
def list_voices():
    """Fetch available voices from ElevenLabs API."""
    api_key = get_elevenlabs_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="ElevenLabs API key missing.")
    try:
        resp = http_requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": api_key}
        )
        resp.raise_for_status()
        data = resp.json()
        voices = []
        for v in data.get("voices", []):
            voices.append({
                "voice_id": v["voice_id"],
                "name": v["name"],
                "category": v.get("category", "unknown"),
                "labels": v.get("labels", {}),
                "preview_url": v.get("preview_url", "")
            })
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chatterbox/voices")
def list_cb_voices():
    """Fetch saved Chatterbox voices."""
    return {"voices": get_cb_voices()}

@app.post("/api/chatterbox/voices")
def add_cb_voice(name: str = Form(...), ref_audio: UploadFile = File(...)):
    voice_id = str(uuid.uuid4())[:8]
    ext = os.path.splitext(ref_audio.filename or "")[1] or ".wav"
    raw_path = os.path.join(VOICES_DIR, f"upload_{voice_id}{ext}")
    wav_path = os.path.join(VOICES_DIR, f"voice_{voice_id}.wav")
    
    import shutil as shutil_mod
    with open(raw_path, "wb") as f:
        shutil_mod.copyfileobj(ref_audio.file, f)
        
    ffmpeg_cmd = r"D:\Program Files\ThirdParty\ffmpeg\bin\ffmpeg.exe"
    if not os.path.exists(ffmpeg_cmd):
        import shutil
        ffmpeg_cmd = shutil.which("ffmpeg") or "ffmpeg"
    
    import subprocess
    try:
        subprocess.run([
            ffmpeg_cmd, "-y",
            "-i", raw_path,
            "-ar", "22050",
            "-ac", "1",
            "-sample_fmt", "s16",
            wav_path
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        print(f"FFmpeg conversion failed: {e}")
        os.rename(raw_path, wav_path)
        
    if os.path.exists(raw_path):
        os.remove(raw_path)
        
    voices = get_cb_voices()
    voices.append({
        "id": voice_id,
        "name": name,
        "path": wav_path
    })
    save_cb_voices(voices)
    
    return {"id": voice_id, "name": name}

@app.delete("/api/chatterbox/voices/{voice_id}")
def delete_cb_voice(voice_id: str):
    voices = get_cb_voices()
    new_voices = []
    deleted = False
    for v in voices:
        if v["id"] == voice_id:
            if os.path.exists(v["path"]):
                try:
                    os.remove(v["path"])
                except:
                    pass
            deleted = True
        else:
            new_voices.append(v)
            
    if deleted:
        save_cb_voices(new_voices)
        return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Voice not found")

@app.post("/api/synthesize")
def synthesize(
    text: str = Form(...),
    engine: str = Form("elevenlabs"),
    voice_id: str = Form(""),
    tone: str = Form("auto"),
    apply_fx: bool = Form(False),
    hesitation: int = Form(0),
    breathiness: int = Form(0),
    target_language: str = Form("english"),
    translate_text: bool = Form(False),
    el_stability: float = Form(0.5),
    el_similarity: float = Form(0.75),
    el_style: float = Form(0.0),
    el_boost: bool = Form(True),
    # Chatterbox advanced parameters (defaults match Chatterbox source)
    cb_exaggeration: float = Form(0.5),
    cb_cfg_weight: float = Form(0.5),
    cb_temperature: float = Form(0.8),
    cb_repetition_penalty: float = Form(1.5),
    cb_top_p: float = Form(1.0),
    cb_min_p: float = Form(0.05),
    cb_voice_id: str = Form(""),
    ref_audio: UploadFile = File(None)
):
    try:
        intent_parser = IntentParser()
        intent = intent_parser.parse_intent(
            text, 
            engine=engine,
            requested_tone=tone,
            hesitation=hesitation,
            breathiness=breathiness,
            target_language=target_language,
            translate_to_native=translate_text
        )
        
        transformer = TextTransformer()
        conditioned_text = transformer.condition_text(text, intent, engine=engine)
        
        # Unique filename per generation
        gen_id = str(uuid.uuid4())[:8]
        raw_filename = f"raw_{gen_id}.wav"
        raw_path = os.path.join(output_dir, raw_filename)
        
        if engine == "elevenlabs":
            api_key = get_elevenlabs_key()
            if not api_key:
                raise HTTPException(status_code=500, detail="ElevenLabs API key missing.")
                
            tts_engine = ElevenLabsEngine(api_key=api_key)
            tts_engine.generate_audio(
                text=conditioned_text,
                voice_id=voice_id,
                output_path=raw_path,
                stability=el_stability,
                similarity=el_similarity,
                style=el_style,
                speaker_boost=el_boost
            )
            
        elif engine == "chatterbox":
            from tts.chatterbox_engine import ChatterboxEngine
            import shutil as shutil_mod
            import subprocess
            
            speaker_wav = None
            if cb_voice_id:
                voices = get_cb_voices()
                for v in voices:
                    if v["id"] == cb_voice_id:
                        speaker_wav = v["path"]
                        break
                if not speaker_wav or not os.path.exists(speaker_wav):
                    raise HTTPException(status_code=400, detail="Saved voice not found.")
            elif ref_audio:
                # Save the uploaded file with its original extension
                ext = os.path.splitext(ref_audio.filename or "")[1] or ".wav"
                uploaded_path = os.path.join(output_dir, f"ref_upload_{gen_id}{ext}")
                with open(uploaded_path, "wb") as f:
                    shutil_mod.copyfileobj(ref_audio.file, f)
                
                # Convert to proper WAV format (22050Hz mono) using FFmpeg
                speaker_wav = os.path.join(output_dir, f"ref_{gen_id}.wav")
                ffmpeg_cmd = r"D:\Program Files\ThirdParty\ffmpeg\bin\ffmpeg.exe"
                if not os.path.exists(ffmpeg_cmd):
                    import shutil
                    ffmpeg_cmd = shutil.which("ffmpeg") or "ffmpeg"
                
                try:
                    print(f"Converting reference audio to WAV for Chatterbox: {speaker_wav}")
                    subprocess.run([
                        ffmpeg_cmd, "-y",
                        "-i", uploaded_path,
                        "-ar", "22050",   # 22050Hz is standard for these models
                        "-ac", "1",       # Mono
                        "-sample_fmt", "s16",
                        speaker_wav
                    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception as e:
                    print(f"FFmpeg conversion failed: {e}")
                    # Fallback: just rename the file
                    os.rename(uploaded_path, speaker_wav)
                
                # Clean up uploaded original
                if os.path.exists(uploaded_path):
                    os.remove(uploaded_path)
            else:
                raise HTTPException(status_code=400, detail="A reference audio file or a saved voice is required for Chatterbox voice cloning.")
                
            chatterbox = ChatterboxEngine()
            chatterbox.generate_audio(
                text=conditioned_text,
                output_path=raw_path,
                audio_prompt_path=speaker_wav,
                language=intent.get("language", "english"),
                exaggeration=cb_exaggeration,
                cfg_weight=cb_cfg_weight,
                temperature=cb_temperature,
                repetition_penalty=cb_repetition_penalty,
                top_p=cb_top_p,
                min_p=cb_min_p,
            )
            
            # Clean up the converted reference file only if it was a one-off upload
            if not cb_voice_id and speaker_wav and os.path.exists(speaker_wav):
                os.remove(speaker_wav)
                
        else:
            raise HTTPException(status_code=400, detail="Unknown engine selected.")
        
        final_filename = f"take_{gen_id}.wav"
        final_path = os.path.join(output_dir, final_filename)
        
        if apply_fx:
            try:
                fx = AudioFX()
                fx.apply_effects(input_path=raw_path, output_path=final_path)
                if os.path.exists(raw_path):
                    os.remove(raw_path)
            except Exception as e:
                print(f"FX failed: {e}")
                if os.path.exists(final_path) and os.path.getsize(final_path) == 0:
                    os.remove(final_path)
                os.rename(raw_path, final_path)
        else:
            os.rename(raw_path, final_path)
            
        mp3_filename = f"take_{gen_id}.mp3"
        mp3_path = os.path.join(output_dir, mp3_filename)
        try:
            convert_to_mp3(final_path, mp3_path)
            final_filename = mp3_filename
        except Exception as e:
            print(f"MP3 conversion failed: {e}")
        
        return {
            "id": gen_id,
            "intent": intent,
            "conditioned_text": conditioned_text,
            "audio_url": f"/static/outputs/{final_filename}",
            "timestamp": time.strftime("%I:%M %p")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/synthesize_conversation")
def synthesize_conversation(req: ConvRequest):
    try:
        import torchaudio
        import torchaudio.transforms as T
        import torch
        
        audio_paths = []
        intents = []
        conditioned_texts = []
        gen_id = str(uuid.uuid4())[:8]
        
        for i, line in enumerate(req.lines):
            if not line.text.strip():
                continue
                
            line_gen_id = f"{gen_id}_L{i}"
            raw_path = os.path.join(output_dir, f"raw_{line_gen_id}.wav")
            
            intent_parser = IntentParser()
            intent = intent_parser.parse_intent(
                line.text, 
                engine=line.engine,
                requested_tone="dramatic",
                target_language=line.target_language,
                translate_to_native=True
            )
            intents.append(intent)
            
            transformer = TextTransformer()
            conditioned_text = transformer.condition_text(line.text, intent, engine=line.engine)
            conditioned_texts.append(conditioned_text)
            
            if line.engine == "elevenlabs":
                api_key = get_elevenlabs_key()
                tts_engine = ElevenLabsEngine(api_key=api_key)
                tts_engine.generate_audio(
                    text=conditioned_text,
                    voice_id=line.voice_id,
                    output_path=raw_path,
                    stability=0.35,
                    similarity=0.85,
                    style=0.3,
                    speaker_boost=True
                )
            elif line.engine == "chatterbox":
                from tts.chatterbox_engine import ChatterboxEngine
                speaker_wav = None
                voices = get_cb_voices()
                for v in voices:
                    if v["id"] == line.voice_id:
                        speaker_wav = v["path"]
                        break
                if not speaker_wav:
                    raise HTTPException(status_code=400, detail=f"Chatterbox voice not found for line {i+1}")
                    
                chatterbox = ChatterboxEngine()
                chatterbox.generate_audio(
                    text=conditioned_text,
                    output_path=raw_path,
                    audio_prompt_path=speaker_wav,
                    language=intent.get("language", "english"),
                    exaggeration=0.75,
                    cfg_weight=0.45,
                    temperature=1.0,
                    repetition_penalty=1.6
                )
            
            if os.path.exists(raw_path):
                audio_paths.append(raw_path)
                
        if not audio_paths:
            raise HTTPException(status_code=400, detail="No audio generated for the conversation.")
            
        target_sr = 44100
        silence_dur = 0.5
        silence_samples = int(target_sr * silence_dur)
        silence_tensor = torch.zeros(1, silence_samples)
        
        final_wavs = []
        for p in audio_paths:
            wav, sr = torchaudio.load(p)
            if wav.shape[0] > 1:
                wav = wav.mean(dim=0, keepdim=True)
            if sr != target_sr:
                resampler = T.Resample(sr, target_sr, dtype=wav.dtype)
                wav = resampler(wav)
            final_wavs.append(wav)
            final_wavs.append(silence_tensor)
            
        if final_wavs:
            final_wavs.pop() # remove trailing silence
            combined = torch.cat(final_wavs, dim=1)
            final_filename = f"take_conv_{gen_id}.wav"
            final_path = os.path.join(output_dir, final_filename)
            torchaudio.save(final_path, combined, target_sr)
            
            if req.apply_fx:
                try:
                    from fx.audio_fx import AudioFX
                    fx = AudioFX()
                    fx_path = os.path.join(output_dir, f"fx_{final_filename}")
                    fx.apply_mastering(final_path, fx_path)
                    if os.path.exists(fx_path):
                        os.replace(fx_path, final_path)
                except Exception as e:
                    print(f"FX failed in conversation mode: {e}")
            
        for p in audio_paths:
            if os.path.exists(p):
                os.remove(p)
                
        mp3_filename = f"take_conv_{gen_id}.mp3"
        mp3_path = os.path.join(output_dir, mp3_filename)
        try:
            convert_to_mp3(final_path, mp3_path)
            final_filename = mp3_filename
        except Exception as e:
            print(f"MP3 conversion failed: {e}")
                
        return {
            "id": gen_id,
            "intent": {"emotion": "mixed", "style": "conversation", "language": "mixed"},
            "conditioned_text": "\n".join(conditioned_texts),
            "audio_url": f"/static/outputs/{final_filename}",
            "timestamp": time.strftime("%I:%M %p")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
