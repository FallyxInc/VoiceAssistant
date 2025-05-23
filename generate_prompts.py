# V2/generate_prompt.py
import openai
import os
import subprocess
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

openai.api_key = os.getenv("OPENAI_API_KEY")

def convert_mp3_to_wav(mp3_file, wav_file):
    """Convert MP3 file to WAV format"""
    subprocess.run(['ffmpeg', '-i', mp3_file, '-y', wav_file], 
                  stdout=subprocess.DEVNULL, 
                  stderr=subprocess.DEVNULL)
    # Remove the temporary MP3 file
    os.remove(mp3_file)

def generate_prompt_audio(text="Hi............. **Jordan.............. Did    you    fall     down?", output_file="audiofiles/prompt.wav"):
    # First generate MP3 (required by OpenAI)
    temp_mp3 = output_file.replace('.wav', '.mp3')
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(temp_mp3, "wb") as f:
        f.write(response.content)
    # Convert to WAV
    convert_mp3_to_wav(temp_mp3, output_file)
    print(f"Generated audio file: {output_file}")

def generate_emergency_audio(text="Ok don't worry, the nurse is coming to help you! Please remain calm and take some deep breaths, everything is going to be okay!", output_file="audiofiles/emergency.wav"):
    temp_mp3 = output_file.replace('.wav', '.mp3')
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(temp_mp3, "wb") as f:
        f.write(response.content)
    convert_mp3_to_wav(temp_mp3, output_file)
    print(f"Generated audio file: {output_file}")

def generate_false_alarm_audio(text="I'm so sorry to disturb you, I just wanted to check if you're okay! Have a great day!", output_file="audiofiles/false_alarm.wav"):
    temp_mp3 = output_file.replace('.wav', '.mp3')
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(temp_mp3, "wb") as f:
        f.write(response.content)
    convert_mp3_to_wav(temp_mp3, output_file)
    print(f"Generated audio file: {output_file}")

def generate_unclear_response_audio(text="I didn't quite understand. Could you please tell me if you fell down or not? I just want to make sure you're safe.", output_file="audiofiles/unclear_response.wav"):
    temp_mp3 = output_file.replace('.wav', '.mp3')
    response = openai.audio.speech.create(
        model="tts-1-hd",
        voice="shimmer",
        input=text
    )
    with open(temp_mp3, "wb") as f:
        f.write(response.content)
    convert_mp3_to_wav(temp_mp3, output_file)
    print(f"Generated audio file: {output_file}")

if __name__ == "__main__":
    generate_prompt_audio()
    generate_emergency_audio()
    generate_false_alarm_audio()
    generate_unclear_response_audio()