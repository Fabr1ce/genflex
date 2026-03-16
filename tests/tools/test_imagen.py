import os
from dotenv import load_dotenv
load_dotenv()
from app.agent import sketch_scene

res = sketch_scene("A happy dog playing in the park")
print("RESULT:", res)
