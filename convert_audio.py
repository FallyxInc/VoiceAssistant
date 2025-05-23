import os
import subprocess
from pathlib import Path

def convert_mp3_to_wav(input_dir):
    # Get the absolute path of the input directory
    input_dir = Path(input_dir).resolve()
    
    # Create output directory if it doesn't exist
    output_dir = input_dir / "wav"
    output_dir.mkdir(exist_ok=True)
    
    # Get all MP3 files in the input directory
    mp3_files = list(input_dir.glob("*.mp3"))
    
    if not mp3_files:
        print("No MP3 files found in the directory.")
        return
    
    print(f"Found {len(mp3_files)} MP3 files to convert.")
    
    # Convert each MP3 file to WAV
    for mp3_file in mp3_files:
        wav_file = output_dir / f"{mp3_file.stem}.wav"
        print(f"Converting {mp3_file.name} to {wav_file.name}...")
        
        try:
            # Use ffmpeg to convert the file
            subprocess.run([
                "ffmpeg",
                "-i", str(mp3_file),
                "-acodec", "pcm_s16le",  # Use 16-bit PCM encoding
                "-ar", "44100",          # Set sample rate to 44.1kHz
                "-ac", "1",              # Set to mono
                str(wav_file)
            ], check=True, capture_output=True)
            print(f"Successfully converted {mp3_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"Error converting {mp3_file.name}: {e.stderr.decode()}")
        except Exception as e:
            print(f"Unexpected error converting {mp3_file.name}: {str(e)}")

def play_audio(file_path, device="plughw:3,0"):
    """
    Play audio file using aplay with specified output device.
    Args:
        file_path: Path to the WAV file
        device: Audio output device (default: plughw:3,0 for Orange Pi)
    """
    try:
        subprocess.run(["aplay", "-D", device, str(file_path)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error playing audio: {e}")
    except Exception as e:
        print(f"Unexpected error playing audio: {str(e)}")

def list_audio_devices():
    """List available audio devices"""
    try:
        subprocess.run(["aplay", "-l"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error listing audio devices: {e}")
    except Exception as e:
        print(f"Unexpected error listing audio devices: {str(e)}")

if __name__ == "__main__":
    # Get the directory of the script
    script_dir = Path(__file__).parent
    audio_dir = script_dir / "general_intelligence"
    
    if not audio_dir.exists():
        print(f"Error: Directory {audio_dir} does not exist.")
    else:
        # First, list available audio devices
        print("Available audio devices:")
        list_audio_devices()
        
        # Convert MP3s to WAV
        convert_mp3_to_wav(audio_dir)
        print("Conversion complete!")
        
        # Example of playing a converted file
        wav_dir = audio_dir / "wav"
        if wav_dir.exists():
            print("\nTesting audio playback...")
            # Play the first WAV file found
            wav_files = list(wav_dir.glob("*.wav"))
            if wav_files:
                print(f"Playing {wav_files[0].name}...")
                play_audio(wav_files[0]) 