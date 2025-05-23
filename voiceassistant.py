import openai
import os
import time
import threading
from datetime import datetime
import requests
from dotenv import load_dotenv
import subprocess

load_dotenv() 

openai.api_key = os.getenv("OPENAI_API_KEY")

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
            # Use aplay with specific device output for Orange Pi
            subprocess.run(["aplay", "-D", "plughw:3,0", output_file])
        else:
            os.system(f"start {output_file}")
    
    threading.Thread(target=play_audio).start()

def play_prompt(output_file="audiofiles/prompt.wav"):
    play_audio_file(output_file)

def play_response_audio(intent):
    if intent == "ok":
        play_audio_file("audiofiles/false_alarm.wav")
    elif intent == "not_ok":
        play_audio_file("audiofiles/emergency.wav")
    elif intent == "unclear":
        play_audio_file("audiofiles/unclear_response.wav")

# Record the response from the user
def record_audio(run_folder, filename="response.wav", duration=10, fs=44100):
    log_interaction("Starting audio recording", run_folder)
    print("Recording response...")
    
    # Use arecord with specific device for Orange Pi
    output_path = os.path.join(run_folder, filename)
    subprocess.run([
        "arecord",
        "-D", "plughw:3,0",
        "-f", "cd",
        "-d", str(duration),
        output_path
    ])
    
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

def call_for_help():
    url = "https://724cu8r3wk.execute-api.ca-central-1.amazonaws.com/Prod/outcall"
    headers = {'Content-Type': 'application/json'}
    data = {
        "emergencyPhoneNumber": EMERGENCYNUMBER,
        "emergencyFirstname": "SRR",
        "userFirstName": "Clay",
        "userLastName": ""
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"Emergency request sent, response status code: {response.status_code}")
    return response.status_code

# Determine if the user is ok or not based on the interaction
def main():
    # Create a new folder for this run
    run_folder = create_run_folder()
    log_interaction("=== Starting new interaction ===", run_folder)
    
    prepare_audio_recording()
    
    max_attempts = 3  # Maximum number of attempts for unclear responses
    attempt = 0
    
    while attempt < max_attempts:
        if attempt == 0:
            play_prompt()
            # First attempt: 6 seconds recording
            audio_path = record_audio(run_folder, duration=6)
        else:
            log_interaction(f"Attempt {attempt + 1}: Asking again after unclear response", run_folder)
            # Follow-up attempts: 10 seconds recording
            audio_path = record_audio(run_folder, duration=10)
        
        transcribed = transcribe_audio(audio_path, run_folder)
        intent = interpret_intent(transcribed, run_folder)

        if intent == "ok":
            log_interaction("Action: False alarm - No action needed", run_folder)
            print("False alarm. No action needed.")
            play_response_audio(intent)
            break
        elif intent == "not_ok":
            log_interaction("Action: Emergency confirmed - Help needed", run_folder)
            print("Emergency confirmed! Calling for help.")
            play_response_audio(intent)
            # Call emergency number
            status_code = call_for_help()
            log_interaction(f"Emergency call initiated with status code: {status_code}", run_folder)
            break
        else:  # unclear
            log_interaction(f"Action: Unclear response on attempt {attempt + 1}", run_folder)
            print(f"Unclear response. Attempt {attempt + 1} of {max_attempts}")
            play_response_audio(intent)
            attempt += 1
            
            if attempt >= max_attempts:
                log_interaction("Action: Maximum attempts reached - Escalating to emergency", run_folder)
                print("Maximum attempts reached. Escalating to emergency response.")
                play_audio_file("audiofiles/emergency.wav")
                status_code = call_for_help()
                log_interaction(f"Emergency call initiated with status code: {status_code}", run_folder)
    
    log_interaction("=== Interaction complete ===\n", run_folder)

if __name__ == "__main__":
    main()