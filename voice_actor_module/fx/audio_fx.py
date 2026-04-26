import subprocess
import os
import shutil

class AudioFX:
    def __init__(self):
        # A professional vocal mastering chain using FFmpeg filters:
        # 1. highpass: Removes low rumble < 70Hz (cleans up mud)
        # 2. equalizer (120Hz): Boosts the "chest" / fundamental frequencies for a deeper, richer "radio" voice
        # 3. equalizer (3000Hz): Boosts presence for crisp articulation and clarity
        # 4. agate: Noise gate to mute completely during pauses (removes AI background hiss)
        # 5. acompressor: Evens out the dynamics so whispers are audible and shouts don't distort
        # 6. alimiter: Pumps the overall loudness to a commercial standard (-1dB ceiling)
        self.mastering_chain = (
            "highpass=f=70,"
            "equalizer=f=120:width_type=h:width=50:g=3,"
            "equalizer=f=3000:width_type=h:width=200:g=2,"
            "agate=threshold=0.015:ratio=3:attack=2:release=100,"
            "acompressor=threshold=-18dB:ratio=4:attack=5:release=50:makeup=3,"
            "alimiter=limit=-1dB"
        )
        
    def apply_effects(self, input_path: str, output_path: str, effects: str = None):
        """
        Apply professional audio mastering using FFmpeg.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        filter_str = effects if effects else self.mastering_chain
        
        ffmpeg_cmd = "ffmpeg"
        hardcoded_path = r"D:\Program Files\ThirdParty\ffmpeg\bin\ffmpeg.exe"
        
        # If the terminal hasn't reloaded the system PATH yet, use the hardcoded path directly
        if not shutil.which("ffmpeg") and os.path.exists(hardcoded_path):
            ffmpeg_cmd = hardcoded_path
            
        command = [
            ffmpeg_cmd,
            "-y", # Overwrite output file
            "-i", input_path,
            "-af", filter_str,
            output_path
        ]
        
        print(f"Applying Studio Mastering to {input_path} using {ffmpeg_cmd}...")
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Processed audio saved to {output_path}")
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e.stderr.decode('utf-8')}")
            raise
        except FileNotFoundError:
            print("FFmpeg not found. Please ensure it is installed and in your PATH.")
            raise
