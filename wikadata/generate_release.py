from pathlib import Path
import shutil
from wikadata.utils.logger import logger


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.resolve().parent / Path("release")

DATA_SOURCES = {
    "dictionaries": Path("wikadata/dictionaries"),
    "freqlists": Path("wikadata/freqlists"),
    "phrasebooks": Path("wikadata/phrasebooks"),
    "wordlists": Path("wikadata/wordlists"),
}


def main():
    clean_release()
    collect_files()
    logger.info("Release data is ready in /release/")


def collect_files():
    """Copy parsed files from all modules into the release directory."""
    for category, base_path in DATA_SOURCES.items():
        output_path = OUTPUT_DIR / category
        output_path.mkdir(parents=True, exist_ok=True)

        search_paths = base_path.glob("processed_data")

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for file in search_path.rglob("*"):
                if not file.is_file():
                    continue

                shutil.copy(file, output_path)
                logger.info(f"Collected {file} to {output_path}")


def clean_release():
    """Remove old release files before generating a new one."""
    if OUTPUT_DIR.exists():
        logger.info("Removed old release files.")
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    main()
