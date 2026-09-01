from bot import enchiridion_run

import os
from dotenv import load_dotenv
from pathlib import Path

base_path = Path(__file__).resolve().parent
env_path = base_path.parent / '.env'
load_dotenv(dotenv_path=env_path)

DEV=False

if DEV:
    enchiridion_run(os.getenv("DEV_TOKEN"))
else:
    enchiridion_run(os.getenv("DISCORD_TOKEN"))