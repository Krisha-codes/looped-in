import json
import time
import webbrowser
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError

from build_page import build_page
from news_tools import get_headlines, get_hacker_news
from weather import get_weather

load_dotenv()

BASE = Path(__file__).parent

# ---------- Settings you can edit ----------
INTERESTS = "mathematics, computer science and programming, basketball, world affairs"
MODELS = ["gemini-3.8-flash", "gemini-3.1-flash-lite"]
MAX_STEPS = 8
# -------------------------------------------

client = genai.Client()

SYSTEM_PROMPT = """You are the editor of "Looped In", a daily briefing for a college student.
The reader's interests: __INTERESTS__. She also wants to be generally well informed about the world.

Process: call get_headlines for the categories you need (world, us, science, business, basketball)
and get_hacker_news. You can call several tools in the same step.

Then choose the stories and reply with ONLY a JSON object (no markdown, no extra text) in exactly this shape:
{
  "headline_story": {"title": "", "blurb": "", "url": "", "source": ""},
  "sections": [
    {"name": "World", "stories": [{"title": "", "blurb": "", "url": "", "source": ""}]}
  ],
  "curveball": {"title": "", "blurb": "", "url": "", "source": ""},
  "one_thing_to_know": ""
}

Rules:
- headline_story: the single most important story of the day.
- 2 to 4 sections (for example World, Tech & CS, Science, Sports), 1 to 3 stories each, 6 to 8 stories in total.
- Don't fill the page with tragedy: at most 3 stories about violence or disasters unless the news truly demands more.
- curveball: one story outside her usual interests, chosen to expand what she knows.
- blurb: exactly 2 sentences covering what happened and why it matters. Use only facts from the tool results.
  If a story gives only a title, write a modest blurb and do not invent details.
- Copy title, url and source exactly from the tool results. Never invent a story or a URL.
- one_thing_to_know: one sentence that ties the day together.
""".replace("__INTERESTS__", INTERESTS)

# ---------- Tools the agent may use ----------
# (weather is not here: plain code fetches it directly, which is cheaper and more reliable)
TOOLS = {
    "get_headlines": get_headlines,
    "get_hacker_news": get_hacker_news,
}

headlines_declaration = {
    "name": "get_headlines",
    "description": "Get the latest news headlines for one category. "
                   "Returns titles, short summaries, and article URLs.",
    "parameters": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["world", "us", "science", "business", "basketball"],
                "description": "Which news category to fetch.",
            }
        },
        "required": ["category"],
    },
}

hacker_news_declaration = {
    "name": "get_hacker_news",
    "description": "Get the top technology and computer science stories "
                   "from Hacker News right now. Returns titles and URLs.",
}

config = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[types.Tool(function_declarations=[
        headlines_declaration,
        hacker_news_declaration,
    ])],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
)


def call_model(contents):
    """Call Gemini with retries; move to the next model if one is busy or out of quota."""
    for model in MODELS:
        for attempt in range(5):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except ServerError as e:
                wait = 5 * 2 ** attempt  # 5s, 10s, 20s, 40s, 80s
                print(f"  {model} busy ({e.code}), waiting {wait}s...")
                time.sleep(wait)
            except ClientError as e:
                if e.code == 404:
                    print(f"  {model} not found, skipping.")
                    break
                if e.code == 429:
                    print(f"  {model} daily limit reached, trying the next model.")
                    break
                raise
    raise RuntimeError("All models unavailable right now. Try again later.")


def collect_urls(result):
    """Gather every article URL a tool returned."""
    return {s["url"] for s in result.get("stories", []) if s.get("url")}


def run_agent(goal):
    contents = [types.Content(role="user", parts=[types.Part(text=goal)])]
    seen_urls = set()  # every URL the tools gave us

    for step in range(1, MAX_STEPS + 1):
        print(f"\n--- Step {step} ---")
        response = call_model(contents)
        contents.append(response.candidates[0].content)

        calls = response.function_calls
        if not calls:
            print("Model is done.")
            return response.text, seen_urls

        result_parts = []
        for call in calls:
            args = dict(call.args or {})
            print(f"Model wants to call: {call.name}({args})")
            result = TOOLS[call.name](**args)
            seen_urls |= collect_urls(result)
            result_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"result": result}
                )
            )
        contents.append(types.Content(role="user", parts=result_parts))

    return None, seen_urls


def parse_json(text):
    """Pull the JSON object out of the model's reply, even if it adds extra text."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON found in the model's reply:\n{text}")
    return json.loads(text[start:end + 1])


def check_urls(briefing, allowed):
    """Drop any story whose URL didn't come from a tool (guards against made-up links)."""
    def ok(story):
        return bool(story) and story.get("url") in allowed

    kept = []
    for section in briefing.get("sections", []):
        stories = [s for s in section.get("stories", []) if ok(s)]
        dropped = len(section.get("stories", [])) - len(stories)
        if dropped:
            print(f"Removed {dropped} story(ies) with unverified links from {section.get('name')}.")
        if stories:
            kept.append({"name": section["name"], "stories": stories})
    briefing["sections"] = kept

    for key in ("headline_story", "curveball"):
        if not ok(briefing.get(key)):
            print(f"Removed {key}: its link was not returned by any tool.")
            briefing[key] = None


def make_briefing():
    text, seen_urls = run_agent("Write today's Looped In briefing.")
    if text is None:
        raise RuntimeError("The agent hit the step limit without finishing.")

    briefing = parse_json(text)
    check_urls(briefing, seen_urls)

    now = datetime.now()
    briefing["date"] = f"{now:%A, %B} {now.day}, {now.year}"
    briefing["weather"] = get_weather()  # plain code, no AI needed
    return briefing


if __name__ == "__main__":
    briefing = make_briefing()

    with open(BASE / "briefing.json", "w", encoding="utf-8") as f:
        json.dump(briefing, f, indent=2, ensure_ascii=False)

    path = build_page(briefing)
    print("\nBuilt:", path)
    if "--no-open" not in sys.argv:
        webbrowser.open(path.as_uri())