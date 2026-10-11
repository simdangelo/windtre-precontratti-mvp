from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def asset_url(name: str) -> str:
    """URL statico con cache-busting basato sulla data di modifica del file."""
    try:
        version = int((STATIC_DIR / name).stat().st_mtime)
    except OSError:
        version = 0
    return f"/static/{name}?v={version}"


templates.env.globals["asset_url"] = asset_url
