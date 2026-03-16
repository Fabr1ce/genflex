import os
from dotenv import load_dotenv
load_dotenv()
from app.agent import generate_audio_narration

res = generate_audio_narration("A happy dog playing in the park")
print("RESULT:", res)
