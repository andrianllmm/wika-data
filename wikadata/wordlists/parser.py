import json
import unicodedata
from pathlib import Path
from wikadata.utils.logger import logger
from wikadata.utils.graceful_exit import on_exit


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    dictionaries_dir = SCRIPT_DIR.parent / "dictionaries"
    wordlists: dict[str, set[str]] = {}

    on_exit(
        lambda: export_wordlists(wordlists),
        message="Process interrupted. Saving word lists...",
    )

    generate_wordlists(dictionaries_dir, wordlists)
    export_wordlists(wordlists)


def generate_wordlists(dictionaries_dir: Path, wordlists: dict[str, set[str]]) -> bool:
    """Generates word lists from parsed dictionaries."""
    for file_path in dictionaries_dir.glob("*/parsed/*.json"):
        logger.info(f"Processing file: {file_path}")

        with file_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
            lang = data["meta"]["lang"]

            wordlists.setdefault(lang, set())

            for entry in data["entries"]:
                normalized_word = strip_diacritics(entry["word"])
                wordlists[lang].add(normalized_word)

    logger.info(f"Generated {len(wordlists)} word lists.")
    return True


def export_wordlists(wordlists: dict[str, set[str]]) -> bool:
    """Exports word lists to JSON files."""
    if not wordlists:
        logger.warning("No word lists to export.")
        return False

    output_dir = SCRIPT_DIR / "processed_data"
    output_dir.mkdir(exist_ok=True)

    for lang, words in wordlists.items():
        output_path = output_dir / f"wordlist_{lang}.txt"
        with output_path.open("w", encoding="utf-8") as file:
            sorted_words = sorted(words)
            file.writelines("\n".join(sorted_words))

    logger.info(f"Word lists successfully exported to {output_dir}.")
    return True


def strip_diacritics(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


if __name__ == "__main__":
    main()
