import json
from collections import defaultdict, OrderedDict
from pathlib import Path
from wikadata.utils.logger import logger


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "processed_data"
PARSED_DIRS = SCRIPT_DIR.glob("*/parsed/*.json")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    merged_phrasebooks = collect_phrasebooks()

    for filename, data in merged_phrasebooks.items():
        filepath = OUTPUT_DIR / filename
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved merged phrasebook: {filename}")

    logger.info("Phrasebooks generated successfully.")


def collect_phrasebooks() -> dict[str, OrderedDict]:
    """Aggregate phrasebook data from all parsed sources."""
    merged_data = defaultdict(lambda: {"meta": OrderedDict(), "entries": []})

    for file in PARSED_DIRS:
        with file.open(encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
            meta = data["meta"]
            entries = data["entries"]

        filename = f"phrasebook_{meta['lang']}_{meta['translation_lang']}.json"

        merged_data[filename]["meta"] = OrderedDict(
            [
                ("lang", meta["lang"]),
                ("translation_lang", meta["translation_lang"]),
            ]
        )
        merged_data[filename]["entries"].extend(
            ensure_ordered_entry(entry, meta) for entry in entries
        )

        logger.info(f"Merged {file} into {filename}")

    return merged_data


def ensure_ordered_entry(entry: dict, meta: OrderedDict) -> OrderedDict:
    """Ensure entry structure with proper order and defaults."""
    translations = [
        ensure_ordered_translation(t, meta) for t in entry.get("translations")
    ]

    data = OrderedDict(
        [
            ("phrase", entry.get("phrase")),
            ("categories", entry.get("categories")),
            ("usage_note", entry.get("usage_note")),
            ("translations", translations),
        ]
    )

    return OrderedDict(filter_empty_fields(data))


def ensure_ordered_translation(translation: dict, meta: OrderedDict) -> OrderedDict:
    """Ensure translation structure with proper order and defaults."""
    data = OrderedDict(
        [
            ("content", translation.get("content")),
            ("examples", translation.get("examples")),
            ("source_title", translation.get("source_title", meta.get("source_title"))),
            ("source_link", translation.get("source_link", meta.get("source_link"))),
        ]
    )

    return filter_empty_fields(data)


def filter_empty_fields(data: OrderedDict) -> OrderedDict:
    """Remove keys with None, empty lists, or empty strings while keeping order."""
    return OrderedDict((k, v) for k, v in data.items() if v not in [None, "", []])


if __name__ == "__main__":
    main()
