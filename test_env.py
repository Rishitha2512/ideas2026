from pathlib import Path
import os
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"

print("Env file exists:", env_path.exists())
print("Env path:", env_path)

load_dotenv(env_path)

print("OPENAI_API_KEY =", repr(os.getenv("OPENAI_API_KEY")))
print("OPENAI_MODEL =", repr(os.getenv("OPENAI_MODEL")))
print("LLM_PROVIDER =", repr(os.getenv("LLM_PROVIDER")))