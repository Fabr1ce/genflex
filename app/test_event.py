import asyncio
from dotenv import load_dotenv
load_dotenv()
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import root_agent

async def run_test():
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="test", app_name="test")
    runner = Runner(agent=root_agent, session_service=session_service, app_name="test")
    
    events = runner.run_async(
        user_id="test",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text="Tell me a story about a brave little toaster. Make it very short.")]),
    )
    
    async for event in events:
        print("author:", getattr(event, "author", "N/A"), "is_final:", getattr(event, "is_final_response", lambda: False)())
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print("  text:", repr(part.text)[:60])
                if getattr(part, "function_response", None):
                    print("  func_resp")

if __name__ == "__main__":
    asyncio.run(run_test())
