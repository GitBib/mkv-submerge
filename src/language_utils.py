LANGUAGE_MAPPING = {
    "ru": ["ru", "rus", "russian"],
    "en": ["en", "eng", "english"],
    "ja": ["ja", "jpn", "japanese"],
    "de": ["de", "ger", "deu", "german"],
    "fr": ["fr", "fre", "fra", "french"],
    "es": ["es", "spa", "spanish"],
    "it": ["it", "ita", "italian"],
    "pt": ["pt", "por", "portuguese"],
    "zh": ["zh", "chi", "zho", "chinese"],
    "ko": ["ko", "kor", "korean"],
    "ar": ["ar", "ara", "arabic"],
    "he": ["he", "heb", "hebrew"],
    "hi": ["hi", "hin", "hindi"],
    "th": ["th", "tha", "thai"],
    "tr": ["tr", "tur", "turkish"],
    "pl": ["pl", "pol", "polish"],
    "nl": ["nl", "dut", "nld", "dutch"],
    "sv": ["sv", "swe", "swedish"],
    "no": ["no", "nor", "norwegian"],
    "da": ["da", "dan", "danish"],
    "fi": ["fi", "fin", "finnish"],
    "cs": ["cs", "cze", "ces", "czech"],
    "sk": ["sk", "slo", "slk", "slovak"],
    "hu": ["hu", "hun", "hungarian"],
    "ro": ["ro", "rum", "ron", "romanian"],
    "bg": ["bg", "bul", "bulgarian"],
    "hr": ["hr", "hrv", "croatian"],
    "sr": ["sr", "srp", "serbian"],
    "uk": ["uk", "ukr", "ukrainian"],
}


def is_language_match(requested_lang: str, track_lang: str) -> bool:
    if not track_lang:
        return False

    requested_lower = requested_lang.lower()
    track_lower = track_lang.lower()

    if requested_lower == track_lower:
        return True

    if requested_lower in LANGUAGE_MAPPING:
        return track_lower in LANGUAGE_MAPPING[requested_lower]

    return any(requested_lower in lang_codes and track_lower in lang_codes for lang_codes in LANGUAGE_MAPPING.values())


def has_language_in_set(requested_lang: str, lang_set: set[str]) -> bool:
    return any(is_language_match(requested_lang, existing_lang) for existing_lang in lang_set)
