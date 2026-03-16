import os
from dotenv import load_dotenv
load_dotenv()
from app.agent_tools import sketch_scene

res = sketch_scene("A brave toaster")
print(res)
