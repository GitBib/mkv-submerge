from pathlib import Path


def read_config(path: str | None) -> dict[str, str | bool | None]:
    if path is None:
        return {}
    try:
        import tomllib
    except ModuleNotFoundError:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    with p.open("rb") as f:
        data = tomllib.load(f)
    section = data.get("mkv_submerge") or data
    return {
        "root": section.get("root"),
        "check_lang": section.get("check_lang"),
        "set_lang": section.get("set_lang"),
        "output_dir": section.get("output_dir"),
        "ai_translated": section.get("ai_translated", False),
        "ignore_mux_errors": section.get("ignore_mux_errors", False),
        "verbose": section.get("verbose", False),
    }
