import json
import time
from google import genai
from google.genai import types
from google.genai.errors import ServerError

# Try the best model first, then fall back to lighter ones if it's busy
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",  # if this gives a 404, copy a current Flash-Lite name from AI Studio
]

client = genai.Client()


def ask_with_fallback(prompt, attempts_per_model=3):
    for model in MODELS:
        for attempt in range(attempts_per_model):
            try:
                print(f"Trying {model} (attempt {attempt + 1})...")
                return client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    ),
                )
            except ServerError as e:
                wait = 2 ** attempt * 2  # 2s, 4s, 8s
                print(f"  Busy ({e.code}), waiting {wait}s...")
                time.sleep(wait)
        print(f"{model} is unavailable, moving to the next model.")
    raise RuntimeError("All models are unavailable right now. Try again later.")


response = ask_with_fallback(
    "Invent a fake newspaper story. Respond with a JSON object "
    "with the fields 'headline' and 'summary'."
)

print("Raw response:", response.text)
story = json.loads(response.text)
print("Headline:", story["headline"])
print("Summary:", story["summary"])