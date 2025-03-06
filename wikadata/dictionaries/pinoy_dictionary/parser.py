import argparse
import json
import re
import sys
from bs4 import BeautifulSoup
from pathlib import Path
from utils.logger import logger
from utils.graceful_exit import on_exit


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    argparser = argparse.ArgumentParser(
        description="Parse dictionary entries from a file scraped from Pinoy Dictionary."
    )
    argparser.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        help="Path to the input file.",
    )
    args = argparser.parse_args()

    input_path = args.input_file
    raw_data, meta = import_raw_data(input_path)
    if not raw_data:
        logger.error("No raw data available.")
        sys.exit(1)

    # Main data store
    parsed_data: list[dict] = []

    on_exit(
        lambda: export_parsed_data(parsed_data, meta),
        message="Process interrupted. Saving processed data...",
    )

    parse(raw_data, parsed_data)
    export_parsed_data(parsed_data, meta)


def parse(raw_data: list[dict], parsed_data: list[dict]) -> bool:
    """Parses dictionary entries."""
    if not raw_data:
        logger.error("No data to process.")
        return False

    for entry in raw_data:
        if processed_entry := process_entry(entry):
            parsed_data.append(processed_entry)

    logger.info(f"Parsing completed. Total entries collected: {len(parsed_data)}")
    return True


def process_entry(entry: dict[str, str]) -> dict | None:
    """Processes a dictionary entry."""
    try:
        word = entry.get("word", "").strip()
        if not word:
            return None

        full_definition = BeautifulSoup(
            entry.get("definition", ""), "html.parser"
        ).get_text(strip=True)
        source = entry.get("source", "")

        logger.info(f"Processing entry: {word}")

        # Remove texts in parentheses in word
        # Example: https://tagalog.pinoydictionary.com/word/abay-mga/
        word = re.sub(r"\(.+?\)", "", word).strip()

        # Remove repeated words separated by a comma
        # Example: https://tagalog.pinoydictionary.com/word/adisyon-adisyon/
        if "," in word:
            word = word.split(",")[0].strip()

        # Remove word that is prefixed in the definition
        # Example: https://tagalog.pinoydictionary.com/word/aalug-alog/
        full_definition = re.sub(f"^{word}", "", full_definition).lstrip(" .,;:!?")

        # Extract inflections (at the start of the definition and enclosed within parentheses)
        # Example: https://tagalog.pinoydictionary.com/word/abain/
        inflections = []
        if inflection_match := re.match(
            r"^\(([^\(\)]*(?:\(.+?\))?[^\(\)]*)\)", full_definition
        ):
            inflections_str = inflection_match.group(1).replace(".", ",").strip()
            inflections = [inf.strip() for inf in inflections_str.split(",")]

            # Remove inflections from definition
            full_definition = full_definition[len(f"({inflections_str})") :].strip()

        # Extract parts of speech (at the start of the definition with a pattern of <pos>., <pos>.; <pos>.)
        # Example: https://tagalog.pinoydictionary.com/word/abahin/
        pos = None
        if pos_match := re.match(r"^((?:(?:\d\. )?[a-z]+\.,?;? ?)+)", full_definition):
            pos = pos_match.group(1).strip()
            full_definition = full_definition[len(pos) :].strip()

        # Split definitions based on numbers (e.g., `1. this; 2) that` → `['this', 'that']`)
        # Example: https://tagalog.pinoydictionary.com/word/abala/
        definitions = (
            [
                {
                    key: value
                    for key, value in {
                        "description": description.strip(" ;"),
                        "pos": pos,
                        "inflections": inflections,
                        "source_link": source,
                    }.items()
                    if value  # Include only non-empty values
                }
                for description in re.split(r"\d+(?:\.|\))\s*", full_definition)
                if description  # Ensure the description is non-empty
            ]
            if full_definition
            else []
        )

        return {"word": word, "definitions": definitions}

    except Exception as e:
        logger.error(
            f"Error processing entry for word '{entry.get('word', 'Unknown')}': {e}"
        )
        return None


def import_raw_data(file_path: Path) -> tuple[list[dict], dict]:
    """Loads data from a file."""
    logger.info(f"Loading data from {file_path}...")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return [], {}

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        meta = data.get("meta", {})
        entries = data.get("entries", [])
        logger.info(f"Successfully loaded {len(entries)} entries from {file_path}")
        return entries, meta
    except Exception as e:
        logger.error(f"Failed to load data: {e}")
        return [], {}


def export_parsed_data(
    parsed_data: list[dict], meta: dict, overwrite: bool = False
) -> bool:
    """Exports processed data to a file."""
    if not parsed_data:
        logger.warning("No data to export.")
        return False

    output_dir = SCRIPT_DIR / "parsed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = f"dictionary_{meta.get('lang', 'unknown')}_{meta.get('definition_lang', 'unknown')}_{meta.get('total_entries', 'unknown')}_{meta.get('date', 'unknown')}_parsed.json"
    output_path = output_dir / output_filename

    if not overwrite:
        counter = 2
        while output_path.exists():
            output_path = (
                output_dir / f"{output_path.stem}_{counter}{output_path.suffix}"
            )
            counter += 1

    json_data = {
        "meta": {
            "lang": meta.get("lang", ""),
            "definition_lang": meta.get("definition_lang", ""),
            "source_title": meta.get("source_title", ""),
            "source_link": meta.get("source_link", ""),
        },
        "entries": parsed_data,
    }

    try:
        output_path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Data successfully exported to: {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        return False


if __name__ == "__main__":
    main()
