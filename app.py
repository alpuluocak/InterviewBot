import os
import openai
from fastapi import FastAPI
from dotenv import load_dotenv


load_dotenv()

openai.api_key = os.getenv("OPEN_AI_KEY")
openai.organization = os.getenv("OPEN_AI_ORG")

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Let's start"}