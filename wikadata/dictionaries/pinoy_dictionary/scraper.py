import argparse
import bs4
import json
from datetime import datetime
from pathlib import Path
from wikadata.utils.logger import logger
from wikadata.utils.graceful_exit import on_exit
from wikadata.utils.fetch_page import fetch_page


SUPPORTED_LANGS = {
    "tgl": "Tagalog",
    "ceb": "Cebuano",
    "hil": "Hiligaynon",
    # "ilo": "Ilocano",
}
DEFINITION_LANG = "eng"
STARTING_LETTERS = "abcdeghijklmnoprstuwxyz"
SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    argparser = argparse.ArgumentParser(
        description="Scrape dictionary entries from Pinoy Dictionary."
    )
    argparser.add_argument(
        "-l",
        "--lang",
        choices=SUPPORTED_LANGS,
        default="tgl",
        help="The language to scrape (e.g., 'tgl', 'ceb'). Defaults to 'tgl'.",
    )
    args = argparser.parse_args()

    lang = args.lang

    # Main data store
    scraped_data: list[dict] = []

    on_exit(
        lambda: export_scraped_data(lang, scraped_data),
        message="Process interrupted. Saving scraped data...",
    )

    scrape(lang, scraped_data)
    export_scraped_data(lang, scraped_data)


def scrape(lang: str, scraped_data: list[dict]) -> bool:
    """Scrapes dictionary entries."""
    for letter in STARTING_LETTERS:
        page_number = 1
        while True:
            logger.info(
                f"Scraping: {lang.upper()} - Letter: {letter.upper()} - Page {page_number}"
            )

            # Construct URL
            base_url = f"https://{SUPPORTED_LANGS[lang].lower()}.pinoydictionary.com/list/{letter}/"
            url = f"{base_url}{page_number}/" if page_number > 1 else base_url

            response = fetch_page(url)

            if not response:
                break

            soup = bs4.BeautifulSoup(response, "html.parser")
            entries: bs4.ResultSet[bs4.element.Tag] = soup.find_all(class_="word-group")
            if not entries:
                logger.info(
                    f"No entries found on page {page_number}. Moving to next letter."
                )
                break

            for entry in entries:
                if processed_entry := process_entry(entry):
                    scraped_data.append(processed_entry)

            page_number += 1

    logger.info(f"Scraping completed. Total entries collected: {len(scraped_data)}")
    return True


def process_entry(entry: bs4.element.Tag) -> dict | None:
    """Processes a dictionary entry."""
    try:
        word_container = entry.find(class_="word")
        word_entry = (
            word_container.find(class_="word-entry") if word_container else None
        )
        word_element = word_entry.find("a") if word_entry else None
        if word_element is None:
            return None

        definition_container = entry.find(class_="definition")
        definition_element = (
            definition_container.find("p") if definition_container else None
        )
        if definition_element is None:
            return None

        word = word_element.text.strip()
        definition = str(definition_element)
        source_url = word_element.get("href")

        logger.info(f"Processing entry: {word}")

        return {
            "word": word,
            "definition": definition,
            "source": source_url,
        }
    except Exception as e:
        logger.error(
            f"Error processing entry for word '{entry.get('word', 'Unknown')}': {e}"
        )
        return None


def export_scraped_data(
    lang: str, scraped_data: list[dict], overwrite: bool = False
) -> bool:
    """Exports scraped data to a JSON file."""
    if not scraped_data:
        logger.warning("No data to export.")
        return False

    current_date = datetime.now().strftime("%Y-%m-%d")

    output_dir = SCRIPT_DIR / "scraped_data"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_filename = (
        f"dictionary_{lang}_{DEFINITION_LANG}_{len(scraped_data)}_{current_date}.json"
    )
    output_path = output_dir / output_filename

    if not overwrite:
        counter = 2
        while output_path.exists():
            output_path = (
                output_dir / f"{output_path.stem}_{counter}{output_path.suffix}"
            )
            counter += 1

    meta = {
        "lang": lang,
        "definition_lang": DEFINITION_LANG,
        "date": current_date,
        "total_entries": len(scraped_data),
        "source_title": f"{SUPPORTED_LANGS[lang]} Pinoy Dictionary",
        "source_link": f"https://{SUPPORTED_LANGS[lang].lower()}.pinoydictionary.com",
    }
    json_data = {
        "meta": meta,
        "entries": scraped_data,
    }

    try:
        output_path.write_text(
            json.dumps(json_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info(f"Data successfully exported to: {output_path}")
        return True
    except IOError as e:
        logger.error(f"Failed to export data: {e}")
        return False


if __name__ == "__main__":
    main()
