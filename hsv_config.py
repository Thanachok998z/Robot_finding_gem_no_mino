import json
from pathlib import Path


# =========================================================
# PATH
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# สำหรับวงกลมใหญ่
CIRCLE_CONFIG_FILE = BASE_DIR / "hsv_config.json"

# สำหรับอัญมณี
GEM_CONFIG_FILE = BASE_DIR / "gem_config.json"


# =========================================================
# CIRCLE
# =========================================================

def load_colors():

    if not CIRCLE_CONFIG_FILE.exists():
        return {}

    try:

        with open(
            CIRCLE_CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            "Load circle config error:",
            e
        )

        return {}


def save_colors(colors):

    try:

        with open(
            CIRCLE_CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                colors,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            "Save circle config error:",
            e
        )

        return False


# =========================================================
# GEM
# =========================================================

def load_gem_colors():

    if not GEM_CONFIG_FILE.exists():
        return {}

    try:

        with open(
            GEM_CONFIG_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except Exception as e:

        print(
            "Load gem config error:",
            e
        )

        return {}


def save_gem_colors(colors):

    try:

        with open(
            GEM_CONFIG_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                colors,
                file,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as e:

        print(
            "Save gem config error:",
            e
        )

        return False