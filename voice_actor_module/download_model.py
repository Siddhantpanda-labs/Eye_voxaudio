import os
import torch

print("Initializing Chatterbox Downloader...")

# Set the local project directory for models so it doesn't use your C: drive
models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "models", "huggingface"))
os.makedirs(models_dir, exist_ok=True)
os.environ["HF_HOME"] = models_dir

print(f"Models will be stored in: {models_dir}")

# Loading the model triggers the download automatically from Hugging Face
try:
    from chatterbox.tts import ChatterboxTTS
    print("\nDownloading Chatterbox Turbo Base Model...")
    model = ChatterboxTTS.from_pretrained(device="cpu") # Use CPU just for download
    
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    print("\nDownloading Chatterbox Multilingual Model...")
    mtl_model = ChatterboxMultilingualTTS.from_pretrained(device="cpu")
    
    print("\n✅ Download complete! Both Chatterbox models are successfully cached in your project directory.")
except Exception as e:
    print(f"\n❌ Error downloading Chatterbox models: {e}")
    print("Make sure you have run 'pip install chatterbox-tts' first.")
