# Phrasebooks

This directory contains the phrasebook data, scrapers, and parsers.

## Data Format

### JSON Phrasebook

```json
{
  "meta": {
    "lang": "ISO 639-3 code",
    "translation_lang": "ISO 639-3 code"
  },
  "entries": [
    {
      "phrase": "Phrase",
      "categories": ["Categories of the phrase"],
      "usage_note": "Usage of the phrase",
      "source_title": "Source title for the phrase",
      "source_link": "Source URL for the phrase",
      "translations": [
        {
          "content": "Translation of the phrase",
          "examples": ["Example sentences of the phrase."],
          "source_title": "Source title for the translation",
          "source_link": "Source URL for the translation"
        }
      ]
    }
  ]
}
```

## Sources

- [Wiktionary](https://en.wiktionary.org/)
