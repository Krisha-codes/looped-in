import json
import webbrowser
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

BASE = Path(__file__).parent


def build_page(briefing, output_name="index.html"):
    """Fill the HTML template with briefing data and save the page."""
    env = Environment(
        loader=FileSystemLoader(BASE / "templates"),
        autoescape=select_autoescape(["html"]),  # keeps odd characters from breaking the page
    )
    template = env.get_template("front_page.html")
    html = template.render(**briefing)

    output_path = BASE / output_name
    output_path.write_text(html, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    # Use the agent's latest briefing if it exists, otherwise the sample
    source = BASE / "briefing.json"
    if not source.exists():
        source = BASE / "sample_briefing.json"

    with open(source, encoding="utf-8") as f:
        briefing = json.load(f)

    path = build_page(briefing)
    print("Built:", path)
    webbrowser.open(path.as_uri())