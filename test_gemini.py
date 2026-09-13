import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ GEMINI_API_KEY is missing from .env")
    raise SystemExit(1)

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents="Say hello to Nova in one short sentence."
    )

    print()
    print("==============================")
    print("      NOVA GEMINI TEST")
    print("==============================")
    print("✅ Gemini API connected!")
    print()
    print("Gemini:", response.text)
    print("==============================")

except Exception as e:
    print()
    print("❌ Gemini connection failed")
    print()
    print(e)