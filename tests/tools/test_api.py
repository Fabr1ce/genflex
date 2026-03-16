import asyncio
from httpx import AsyncClient

async def run():
    async with AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8080/story", 
            json={"prompt": "A brave toaster"},
            timeout=120.0
        )
        print("Status:", resp.status_code)
        try:
            print(resp.json())
        except Exception as e:
            print("Error parsing json:", e, resp.text)

if __name__ == "__main__":
    asyncio.run(run())
