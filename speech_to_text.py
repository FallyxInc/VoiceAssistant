import openai
import sounddevice as sd
import numpy as np
from scipy.io.wavfile import write
import os
import time
import threading
from datetime import datetime

# OpenAI API Key
openai.api_key = "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"

def create_run_folder():
    # Create runs directory if it doesn't exist
    os.makedirs("runs", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"run_{timestamp}"
    folder_path = os.path.join("runs", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path

def log_interaction(message, run_folder):
    log_file = os.path.join(run_folder, "interaction_log.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def prepare_audio_recording(fs=44100):
    sd.default.samplerate = fs
    sd.default.channels = 1
    sd.default.dtype = 'int16'

def play_audio_file(output_file):
    def play_audio():
        if os.name == 'posix':
            os.system(f"afplay {output_file}")
        else:
            os.system(f"start {output_file}")
    
    threading.Thread(target=play_audio).start()

def play_prompt(output_file="audiofiles/prompt.mp3"):
    play_audio_file(output_file)

def play_response_audio(intent):
    if intent == "ok":
        play_audio_file("audiofiles/false_alarm.mp3")
    elif intent == "not_ok":
        play_audio_file("audiofiles/emergency.mp3")

# Record the response from the user
def record_audio(run_folder, filename="response.wav", duration=5, fs=44100):
    log_interaction("Starting audio recording", run_folder)
    print("Recording response...")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()
    output_path = os.path.join(run_folder, filename)
    write(output_path, fs, audio)
    log_interaction(f"Audio recording saved to {output_path}", run_folder)
    print("Recording complete.")
    return output_path

# Using Whisper to transcribe the audio
def transcribe_audio(audio_path, run_folder):
    log_interaction("Starting audio transcription", run_folder)
    print("Transcribing...")
    with open(audio_path, "rb") as f:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=f
        )
    log_interaction(f"Transcription: {transcript.text}", run_folder)
    print("Transcription:", transcript.text)
    return transcript.text

# Interpret the text using GPT to ensure that we get an accurate classification
def interpret_intent(text, run_folder):
    log_interaction("Starting intent classification", run_folder)
    prompt = f"""
An elderly person was asked: "Did you fall?".
They responded: "{text}"

Classify the intent into one of:
- 'ok' (they explicitly state they did NOT fall or are fine, regardless of tone or additional words)
- 'not_ok' (they explicitly state they DID fall or need help)
- 'unclear' (ambiguous or unrelated response)

Examples:
- "No, I'm fine" -> ok
- "No, I didn't fall" -> ok
- "No, go away" -> ok
- "Yes, I fell" -> not_ok
- "Help me" -> not_ok
- "What?" -> unclear
- "I'm hungry" -> unclear

Only return one of: ok, not_ok, unclear.
"""

    print("Classifying intent...")
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    intent = response.choices[0].message.content.strip()
    log_interaction(f"Detected intent: {intent}", run_folder)
    print("Detected intent:", intent)
    return intent

# Determine if the user is ok or not based on the interaction
def main():
    # Create a new folder for this run
    run_folder = create_run_folder()
    log_interaction("=== Starting new interaction ===", run_folder)
    
    prepare_audio_recording()
    
    play_prompt()
    audio_path = record_audio(run_folder)
    transcribed = transcribe_audio(audio_path, run_folder)
    intent = interpret_intent(transcribed, run_folder)

    if intent == "ok":
        log_interaction("Action: False alarm - No action needed", run_folder)
        print("False alarm. No action needed.")
        play_response_audio(intent)
    elif intent == "not_ok":
        log_interaction("Action: Emergency confirmed - Help needed", run_folder)
        print("Emergency confirmed! Calling for help.")
        play_response_audio(intent)
    else:
        log_interaction("Action: Unclear response - Consider escalation", run_folder)
        print("Unclear. Consider asking again or escalating.")
    
    log_interaction("=== Interaction complete ===\n", run_folder)

if __name__ == "__main__":
    main()