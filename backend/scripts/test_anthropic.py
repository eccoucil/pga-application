import asyncio
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

async def test_anthropic_connectivity():
    # Load env from backend/.env
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found in .env")
        return

    print(f"Checking connectivity to Anthropic API...")
    print(f"API Key length: {len(api_key)}")
    
    urls = [
        "https://api.anthropic.com",
        "https://api.anthropic.com/v1/messages"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for url in urls:
            try:
                print(f"
Testing {url}...")
                # Basic GET to check if we can even reach the domain
                response = await client.get(url)
                print(f"✅ Reached {url}. Status: {response.status_code}")
            except Exception as e:
                print(f"❌ Failed to reach {url}: {type(e).__name__}: {e}")
                
    # Test with standard Anthropic SDK structure but raw httpx
    print("
Testing TLS Handshake with HTTP/1.1 specifically...")
    try:
        async with httpx.AsyncClient(http2=False, timeout=10.0) as client:
            response = await client.get("https://api.anthropic.com")
            print(f"✅ HTTP/1.1 Success. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTP/1.1 Failure: {e}")

    print("
Testing TLS Handshake with HTTP/2...")
    try:
        async with httpx.AsyncClient(http2=True, timeout=10.0) as client:
            response = await client.get("https://api.anthropic.com")
            print(f"✅ HTTP/2 Success. Status: {response.status_code}")
    except Exception as e:
        print(f"❌ HTTP/2 Failure: {e}")

if __name__ == "__main__":
    asyncio.run(test_anthropic_connectivity())
