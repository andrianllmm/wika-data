import json
from collections import defaultdict, OrderedDict
from pathlib import Path
from wikadata.utils.logger import logger


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "processed_data"
PARSED_DIRS = SCRIPT_DIR.glob("*/parsed/*.json")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    merged_dictionaries = collect_dictionaries()

    for filename, data in merged_dictionaries.items():
        filepath = OUTPUT_DIR / filename
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved merged dictionary: {filename}")

    logger.info("Dictionaries generated successfully.")


def collect_dictionaries() -> dict[str, OrderedDict]:
    """Aggregate dictionary data from all parsed sources."""
    merged_data = defaultdict(lambda: {"meta": OrderedDict(), "entries": []})

    for file in PARSED_DIRS:
        with file.open(encoding="utf-8") as f:
            data = json.load(f, object_pairs_hook=OrderedDict)
            meta = data["meta"]
            entries = data["entries"]

        filename = f"dictionary_{meta['lang']}_{meta['definition_lang']}.json"

        merged_data[filename]["meta"] = OrderedDict(
            [
                ("lang", meta["lang"]),
                ("definition_lang", meta["definition_lang"]),
            ]
        )
        merged_data[filename]["entries"].extend(
            ensure_ordered_entry(entry, meta) for entry in entries
        )

        logger.info(f"Merged {file} into {filename}")

    return merged_data


def ensure_ordered_entry(entry: dict, meta: OrderedDict) -> OrderedDict:
    """Ensure entry structure with proper order and defaults."""
    definitions = [
        ensure_ordered_definition(d, meta) for d in entry.get("definitions", [])
    ]

    data = OrderedDict(
        [
            ("word", entry.get("word")),
            ("definitions", definitions),
        ]
    )

    return filter_empty_fields(data)


def ensure_ordered_definition(definition: dict, meta: OrderedDict) -> OrderedDict:
    """Ensure definition structure with proper order and defaults."""
    data = OrderedDict(
        [
            ("description", definition.get("description")),
            ("pos", definition.get("pos")),
            ("origin", definition.get("origin")),
            ("usage_note", definition.get("usage_note")),
            ("synonyms", definition.get("synonyms", [])),
            ("antonyms", definition.get("antonyms", [])),
            ("inflections", definition.get("inflections", [])),
            ("examples", definition.get("examples", [])),
            ("source_title", definition.get("source_title", meta["source_title"])),
            ("source_link", definition.get("source_link", meta.get("source_link"))),
        ]
    )

    return filter_empty_fields(data)


def filter_empty_fields(data: OrderedDict) -> OrderedDict:
    """Remove keys with None, empty lists, or empty strings while keeping order."""
    return OrderedDict((k, v) for k, v in data.items() if v not in [None, "", []])


if __name__ == "__main__":
    main()
