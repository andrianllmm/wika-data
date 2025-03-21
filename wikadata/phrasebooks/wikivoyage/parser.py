import argparse
import json
import sys
from bs4 import BeautifulSoup
from pathlib import Path
from wikadata.utils.logger import logger
from wikadata.utils.graceful_exit import on_exit


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    argparser = argparse.ArgumentParser(
        description="Parse phrasebook entries from a file scraped from Wikivoyage."
    )
    argparser.add_argument(
        "input_files",
        nargs="*",
        type=Path,
        help="Paths to the input files.",
    )
    args = argparser.parse_args()

    input_files = args.input_files
    input_paths = (
        input_files
        if input_files
        else [path for path in (SCRIPT_DIR / "scraped_data").glob("*.json")]
    )

    for input_path in input_paths:
        logger.info(f"Processing file: {input_path}")

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
    """Parses phrasebook entries."""
    if not raw_data:
        logger.error("No data to process.")
        return False

    for entry in raw_data:
        if processed_entry := process_entry(entry):
            parsed_data.append(processed_entry)

    logger.info(f"Parsing completed. Total entries collected: {len(parsed_data)}")
    return True


def process_entry(entry: dict[str, str]) -> dict | None:
    """Processes a phrasebook entry."""
    try:
        phrase = BeautifulSoup(entry.get("phrase", ""), "html.parser").get_text(
            strip=True
        )
        if not phrase:
            return None

        full_translation = BeautifulSoup(
            entry.get("translation", ""), "html.parser"
        ).get_text(strip=True)
        category = entry.get("category", "").lower()
        source = entry.get("source", "")

        logger.info(f"Processing entry: {phrase}")

        translations = (
            [{"content": full_translation.strip()}] if full_translation else []
        )

        return {
            key: value
            for key, value in {
                "phrase": phrase,
                "categories": [category] if category else [],
                "source_link": source,
                "translations": translations,
            }.items()
            if value
        }

    except Exception as e:
        logger.error(
            f"Error processing entry for phrase '{entry.get('phrase', 'Unknown')}': {e}"
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

    output_filename = f"phrases_{meta.get('lang', 'unknown')}_{meta.get('translation_lang', 'unknown')}_{meta.get('total_entries', 'unknown')}_{meta.get('date', 'unknown')}_parsed.json"
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
            "translation_lang": meta.get("translation_lang", ""),
            "source_title": meta.get("source_title", ""),
            "source_link": meta.get("source_link", ""),
        },
        "entries": parsed_data,
    }

    try:
        output_path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Data successfully exported to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        return False


if __name__ == "__main__":
    main()
