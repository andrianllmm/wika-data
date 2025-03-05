import csv
import sys
from pathlib import Path
from wikadata.utils.logger import logger
from wikadata.utils.graceful_exit import on_exit

csv.field_size_limit(sys.maxsize)


SCRIPT_DIR = Path(__file__).resolve().parent


def main():
    wordlists_dir = SCRIPT_DIR.parent / "wordlists" / "processed_data"
    freqlists: dict[str, dict[str, int]] = {}

    on_exit(
        lambda: export_freqlists(freqlists),
        message="Process interrupted. Saving frequency lists...",
    )

    generate_freqlists(wordlists_dir, freqlists)
    export_freqlists(freqlists)


def generate_freqlists(
    wordlists_dir: Path, freqlists: dict[str, dict[str, int]]
) -> bool:
    """Generate frequency lists from parsed word lists and existing frequency lists."""
    for file_path in wordlists_dir.glob("*.txt"):
        # Assumes filename format: <prefix>_<lang>.txt
        try:
            lang = file_path.stem.split("_")[1]
        except IndexError:
            logger.warning(
                f"Filename {file_path.name} does not match expected format. Skipping."
            )
            continue

        logger.info(f"Processing '{lang}' word list: {file_path}")

        freqlists.setdefault(lang, {})

        with file_path.open("r", encoding="utf-8") as file:
            for line in file:
                if word := line.strip().lower():
                    freqlists[lang][word] = freqlists[lang].get(word, 0) + 1

        apply_existing_freqlist(freqlists, lang)

    logger.info(f"Generated {len(freqlists)} frequency lists.")
    return True


def apply_existing_freqlist(freqlists: dict[str, dict[str, int]], lang: str) -> bool:
    """Apply existing frequency list data from the Leipzig corpus."""
    dir = SCRIPT_DIR / "raw_data" / "leipzig"

    source_file = next(dir.glob(f"{lang}_*"), None)
    if source_file is None:
        logger.warning(f"No frequency list source file found for {lang}.")
        return False

    logger.info(f"Applying existing '{lang}' frequency list: {source_file}.")

    with source_file.open("r", encoding="utf-8") as file:
        reader = csv.reader(file, delimiter="\t")
        for row in reader:
            if len(row) < 2:
                continue

            word = row[1].lower()
            try:
                freq = int(row[-1])
            except ValueError:
                continue

            if word in freqlists[lang]:
                freqlists[lang][word] = freqlists[lang].get(word, 0) + freq

    return True


def export_freqlists(freqlists: dict[str, dict[str, int]]) -> bool:
    """Export frequency lists to CSV files."""
    if not freqlists:
        logger.warning("No word lists to export.")
        return False

    output_dir = SCRIPT_DIR / "processed_data"
    output_dir.mkdir(exist_ok=True)

    for lang, words in freqlists.items():
        output_path = output_dir / f"freqlist_{lang}.csv"
        with output_path.open("w", newline="") as output_file:
            writer = csv.writer(output_file)
            sorted_words = sorted(words.items(), key=lambda item: item[1], reverse=True)
            for word, freq in sorted_words:
                writer.writerow([word, freq])

    logger.info(f"Frequency lists exported to {output_dir}.")
    return True


if __name__ == "__main__":
    main()
