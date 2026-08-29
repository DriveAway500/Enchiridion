import json
from pathlib import Path
import aiofiles

TRANSLATE_DIR = Path(__file__).parent / "translations"


async def load_command_translation(command, language, key=None):
    file_path = TRANSLATE_DIR / f"{command}_{language}.json"

    try:
        async with aiofiles.open(
            file_path, mode="r", encoding="utf-8"
        ) as file:
            content = await file.read()
            data = json.loads(content)

            if key is not None:
                if key in data:
                    return data[key]
                raise KeyError(
                    f"Key '{key}' was not found in file '{file_path.name}'."
                )

            return data
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Translation '{language}' for command '{command}' was not found at '{file_path}'."
        )
    except json.JSONDecodeError:
        raise ValueError(
            f"The file '{file_path}' contains invalid JSON."
        )