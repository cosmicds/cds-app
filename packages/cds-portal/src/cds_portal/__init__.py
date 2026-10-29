from pathlib import Path

from dotenv import load_dotenv

# Load .env from the working directory first; fall back to docker dev env.
_docker_env = Path(__file__).parents[4] / "docker" / "cds-portal" / ".env"
load_dotenv() or load_dotenv(_docker_env)
