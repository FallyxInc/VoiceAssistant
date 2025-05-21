import speech_recognition as sr
from openai import OpenAI
import os
import requests
from dotenv import load_dotenv
from playsound import playsound

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

EMERGENCYNUMBER = os.getenv('EMERGENCYNUMBER')  # Set your emergency number here or in .env

def speak_response(response):
    """Convert text response to speech using OpenAI TTS and play it back"""
    speech_response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=response
    )
    speech_response.stream_to_file("response.mp3")
    playsound("response.mp3")

def call_for_help():
    url = "https://724cu8r3wk.execute-api.ca-central-1.amazonaws.com/Prod/outcall"
    headers = {'Content-Type': 'application/json'}
    data = {
        "emergencyPhoneNumber": EMERGENCYNUMBER,
        "emergencyFirstname": "SRR",
        "userFirstName": "",
        "userLastName": ""
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"Emergency request sent, response status code: {response.status_code}")
    # Play a TTS message for reassurance
    reassurance = "Ok, don't worry, the nurse is coming to help you. Please remain calm."
    speech_response = client.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=reassurance
    )
    speech_response.stream_to_file("emergency.mp3")
    playsound("emergency.mp3")

def listen_to_speech():
    """Listen to user's speech and convert to text"""
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        
    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("Could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results; {e}")
        return None

def analyze_with_openai(text):
    """Analyze text using OpenAI to determine if help is needed"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI that analyzes if someone needs help based on their speech. Respond with 'HELP_NEEDED' if they need help, or 'NO_HELP_NEEDED' if they don't."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error analyzing with OpenAI: {e}")
        return None

def main():
    print("Starting help detection system...")
    speak_response("Please speak clearly into the microphone.")
    
    while True:
        # Listen for speech
        text = listen_to_speech()
        if not text:
            continue
            
        # Analyze if help is needed
        analysis = analyze_with_openai(text)
        
        if analysis == "HELP_NEEDED":
            response = "I detect that you might need help. Calling for assistance now."
            print(response)
            speak_response(response)
            call_for_help()
        elif analysis == "NO_HELP_NEEDED":
            response = "I don't detect any immediate need for help. Let me know if you need anything!"
            print(response)
            speak_response(response)
        else:
            print("Could not determine if help is needed.")

if __name__ == "__main__":
    main()
