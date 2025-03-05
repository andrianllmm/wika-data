import argparse
import concurrent.futures
import json
import string
from pathlib import Path
from bs4 import BeautifulSoup
from html import unescape
from itertools import repeat
from wikadata.utils.logger import logger
from wikadata.utils.graceful_exit import on_exit


SCRIPT_DIR = Path(__file__).resolve().parent
STARTING_LETTERS = set(string.ascii_lowercase)


def main():
    argparser = argparse.ArgumentParser(
        description="Parse dictionary entries from GCIDE_XML."
    )
    default_input_dir = SCRIPT_DIR / "raw_data" / "gcide_xml-0.53"
    argparser.add_argument(
        "input_dir",
        nargs="?",
        default=str(default_input_dir),
        help="Path to the input directory. Defaults to 'raw_data/gcide_xml-0.53/'.",
    )
    args = argparser.parse_args()

    input_dir = Path(args.input_dir)

    # Main data store
    parsed_data: list[dict] = []

    # Handle graceful exit
    on_exit(
        lambda: export_parsed_data(parsed_data),
        message="Process interrupted. Saving processed data...",
    )

    parse(parsed_data, input_dir)
    export_parsed_data(parsed_data)


def parse(parsed_data: list[dict], dir_path: Path) -> bool:
    """Parses dictionary entries."""
    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(process_letter, STARTING_LETTERS, repeat(dir_path))
        for result in results:
            parsed_data.extend(result)
    logger.info(f"Parsing completed. Total entries collected: {len(parsed_data)}")
    return True


def process_letter(letter: str, dir_path: Path) -> list[dict]:
    """Processes dictionary entries that start with a specified letter."""
    file_path = dir_path / f"gcide_{letter}.xml"
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return []

    soup = BeautifulSoup(content, "lxml")
    entries = soup.find_all("p")
    data = []

    for entry in entries:
        if new_entry := process_entry(entry):
            # New word
            if new_entry.get("word"):
                data.append(new_entry)
            # Previous word: if word not present and there's a previous word, append definitions.
            elif data:
                data[-1]["definitions"].extend(new_entry["definitions"])

    return data


def process_entry(entry: BeautifulSoup) -> dict | None:
    """Processes a dictionary entry."""
    try:
        word = None
        if word_xml := entry.find("ent"):
            word = word_xml.get_text(strip=True)
            logger.info(f"Processing entry: {word}")

        pos_xml = entry.find("pos")
        descriptions_xml = entry.find_all("def")
        origin_xml = entry.find("ety")
        synonyms_xml = entry.find("syn")
        antonyms_xml = entry.find("ant")
        sources_xml = entry.find_all("source")
        example_xml = entry.find("q") if entry.find("qex") else None

        pos = pos_xml.get_text(strip=True) if pos_xml else None
        descriptions = (
            [unescape(d.get_text(strip=True)) for d in descriptions_xml]
            if descriptions_xml
            else []
        )
        origin = unescape(origin_xml.get_text().strip(" []")) if origin_xml else None
        synonyms = (
            [
                word.strip().lower()
                for word in synonyms_xml.get_text(strip=True)
                .replace("Syn. --", "")
                .split(",")
            ]
            if synonyms_xml
            else []
        )
        antonyms = (
            [
                word.strip().lower()
                for word in antonyms_xml.get_text(strip=True).split(";")
            ]
            if antonyms_xml
            else []
        )
        source = sources_xml[0].get_text(strip=True) if sources_xml else ""
        examples = [unescape(example_xml.get_text(strip=True))] if example_xml else []

        definitions = []
        for description in descriptions:
            definitions.append(
                {
                    key: value
                    for key, value in {
                        "description": description,
                        "pos": pos,
                        "origin": origin,
                        "synonyms": synonyms,
                        "antonyms": antonyms,
                        "examples": examples,
                        "source_title": source,
                    }.items()
                    if value
                }
            )

        return {"word": word, "definitions": definitions}

    except Exception as e:
        logger.error(f"Error processing entry: {e}")
        return None


def export_parsed_data(parsed_data: list[dict], overwrite: bool = False) -> bool:
    """Exports parsed data to a JSON file."""
    if not parsed_data:
        logger.warning("No data to export.")
        return False

    parsed_data.sort(key=lambda entry: entry["word"].lower())
    output_dir = SCRIPT_DIR / "parsed"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"dictionary_eng_eng_{len(parsed_data)}.json"

    if not overwrite:
        counter = 2
        base = output_path.stem
        ext = output_path.suffix
        while output_path.exists():
            output_path = output_dir / f"{base}_{counter}{ext}"
            counter += 1

    json_data = {
        "meta": {
            "lang": "eng",
            "definition_lang": "eng",
            "total_entries": len(parsed_data),
            "source_title": "GCIDE",
            "source_link": "https://ibiblio.org/webster/",
        },
        "entries": parsed_data,
    }

    try:
        with output_path.open("w", encoding="utf-8") as file:
            json.dump(json_data, file, indent=2, ensure_ascii=False)
        logger.info(f"Data successfully exported to:\n{output_path}")
        return True
    except IOError as e:
        logger.error(f"Failed to export data: {e}")
        return False


if __name__ == "__main__":
    main()
