import os
import openai
import json
import requests
import datetime

from fastapi import FastAPI, UploadFile, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from fastapi import Depends, FastAPI

from fastapi_limiter.depends import RateLimiter

# @asynccontextmanager
# async def lifespan(_: FastAPI):
#     redis_connection = redis.from_url("redis://localhost:6379", encoding="utf8")
#     await FastAPILimiter.init(redis_connection)
#     yield
#     await FastAPILimiter.close()


load_dotenv()

openai.api_key = os.getenv("OPEN_AI_KEY")
openai.organization = os.getenv("OPEN_AI_ORG")
elevenlabs_key = os.getenv("ELEVENLABS_KEY")

app = FastAPI()

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain('cert.pem', keyfile='key.pem')

origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://16.171.32.70:8000",
    "http://16.171.32.70:8000/talk",
    "http://16.171.32.70:8000/clear",
    "http://www.alpsinterviewbot.com",
    "http://alps-interview-bot.com",
    "http://www.alps-interview-bot.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CustomRateLimiter(RateLimiter):
    async def __call__(self, request: Request):
        response = await super().__call__(request)
        if response.status_code == 429:
            raise HTTPException(
                status_code=429, detail="Too many requests. Try again later."
            )
        return response


async def custom_dependency():
    return CustomRateLimiter(times=5, seconds=240)


@app.get("/")
async def root():
    return {"message": "You are in the root directory."}


@app.post("/talk", dependencies=[Depends(custom_dependency)])
async def post_audio(file: UploadFile):
    user_message = transcribe_audio(file)
    chat_response = get_chat_response(user_message)
    audio_output = text_to_speech(chat_response)

    def iterfile():
        yield audio_output

    return StreamingResponse(iterfile(), media_type="application/octet-stream")


@app.get("/clear")
async def clear_history():
    file = 'database.json'
    open(file, 'w')
    return {"message": "Chat history has been cleared"}


def transcribe_audio(file):
    # Save the blob first
    with open(file.filename, 'wb') as buffer:
        buffer.write(file.file.read())
    audio_file = open(file.filename, "rb")
    transcript = openai.Audio.translate("whisper-1", audio_file)
    print(transcript)
    return transcript


def save_messages(user_messages, gpt_response):
    file = 'database.json'
    messages = load_messages()
    messages.append({"role": "user", "content": user_messages['text']})
    messages.append({"role": "assistant", "content": gpt_response})

    if len(gpt_response) > 200:
        raise KeyError('Uzun cevap verdin.')

    timestamp = datetime.datetime.today().timestamp()

    desktop_path = os.path.join(os.path.expanduser("~"), "/home/ec2-user")
    file_path = os.path.join(desktop_path, f"bot_data/database_{timestamp}.json")

    with open(file, 'w') as f:
        json.dump(messages, f)

    # with open(file_path, 'w') as f:
    #     json.dump(messages, f)


def get_chat_response(user_messages):
    messages = load_messages()
    messages.append({"role": "user", "content": user_messages['text']})

    # Send to openAI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=250
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
                         "content": "You are interviewing the user for a position at company. First ask user's name and the position he/she is applying and wait for reply. Ask short questions that are relevant for that position. Never use more than 20 words. After the interview, explain your decision to the candidate"
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
