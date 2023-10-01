import os
import openai
import json
import requests
from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPEN_AI_KEY")
openai.organization = os.getenv("OPEN_AI_ORG")
elevenlabs_key = os.getenv("ELEVENLABS_KEY")

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Let's start"}


@app.post("/talk")
async def post_audio(file: UploadFile):
    user_message = transcribe_audio(file)
    chat_response = get_chat_response(user_message)
    audio_output = text_to_speech(chat_response)
    def iterfile():
        yield audio_output

    return StreamingResponse(iterfile(), media_type="application/octet-stream")


def transcribe_audio(file):
    audio_file = open(file.filename, "rb")
    transcript = openai.Audio.translate("whisper-1", audio_file)
    # transcript = {"role": "user", "content": "Who won the world series in 2020?"}
    print(transcript)
    return transcript


def save_messages(user_messages, gpt_response):
    file = 'database.json'
    messages = load_messages()
    messages.append({"role": "user", "content": user_messages})
    messages.append({"role": "assistant", "content": gpt_response})

    with open(file, 'w') as f:
        json.dump(messages, f)


def get_chat_response(user_messages):
    messages = load_messages()
    messages.append({"role": "user", "content": user_messages['text']})

    # Send to openAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    parsed_gpt_response = response['choices'][0]['message']['content']

    # Save messages
    save_messages(user_messages, parsed_gpt_response)

    return parsed_gpt_response


def load_messages():
    messages = []
    file = 'database.json'

    # If the file is empty, add content
    empty = os.stat(file).st_size == 0

    if not empty:
        with open(file) as db_file:
            data = json.load(db_file)
            for item in data:
                messages.append(item)
    else:
        messages.append({"role": "system",
                         "content": "You are interviewing the user for a business analyst position for the sales department of Bosch. Ask short questions that are relevant for a junior analyst. Your name is Chris. The user is Bora. Keep responses under 50 words and be funny sometimes."
                         })

    return messages


def text_to_speech(text):
    body = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0,
            "similarity_boost": 0,
            "style": 0,
            "use_speaker_boost": True

        }
    }

    headers = {
        "Content-Type": "application/json",
        "accept": "audio/mp",
        "xi-api-key": elevenlabs_key
    }

    url = "https://api.elevenlabs.io/v1/text-to-speech/t0jbNlBVZ17f02VDIeMI"

    try:
        elevenlabs_response = requests.post(url, json=body, headers=headers)
        if elevenlabs_response.status_code == 200:
            return elevenlabs_response.content
        else:
            print("Something went wrong")
    except Exception as e:
        print(e)