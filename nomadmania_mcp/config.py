import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

TOKEN = os.environ.get("NM_TOKEN")
CACHE_DIR = Path(os.environ.get("NM_CACHE_DIR", Path.home() / ".cache" / "nomadmania-mcp"))
