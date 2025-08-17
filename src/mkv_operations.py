import tempfile
from pathlib import Path

import typer
from natsort import natsorted
from pymkv import MKVFile, MKVTrack


def probe_subtitle_languages(mkv_path: Path, verbose: bool = False) -> set[str]:
    if verbose:
        typer.echo(f"Probing subtitle languages in: {mkv_path}")
    try:
        mkv = MKVFile(mkv_path)
        langs = set()
        for track in mkv.tracks:
            if track.track_type != "subtitles":
                continue
            if track.language:
                langs.add(track.language.lower())
        if verbose:
            typer.echo(f"Found subtitle languages: {langs}")
        return langs
    except Exception as e:
        typer.secho(f"Failed to probe subtitle languages in {mkv_path}: {e}", fg="yellow", err=True)
        return set()


def find_srt_file(mkv_path: Path, check_lang: str, verbose: bool = False) -> Path | None:
    if not check_lang:
        return None
    lang = check_lang.lower()
    if verbose:
        typer.echo(f"Looking for {lang} subtitles for: {mkv_path.name}")

    exact = mkv_path.with_suffix(f".{lang}.srt")
    if exact.exists():
        if verbose:
            typer.echo(f"Found exact match: {exact.name}")
        return exact

    stem = mkv_path.with_suffix("").name
    pattern = f"{stem}.*.{lang}.srt"
    if candidates := list(mkv_path.parent.glob(pattern)):
        selected = natsorted(candidates)[0]
        if verbose:
            typer.echo(f"Found pattern match: {selected.name} (from {len(candidates)} candidates)")
        return selected

    if verbose:
        typer.echo(f"No {lang} subtitles found for: {mkv_path.name}")
    return None


def compute_output_path(mkv_path: Path, root: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return mkv_path
    out = Path(output_dir)
    try:
        rel = mkv_path.relative_to(root)
    except Exception:
        rel = Path(mkv_path.name)
    target = out / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def create_subtitle_track(srt_path: Path, lang: str, is_ai_translated: bool = False, verbose: bool = False) -> MKVTrack:
    track = MKVTrack(srt_path)

    try:
        track.language = lang
        if verbose:
            typer.echo(f"Set track language to: {lang}")
    except ValueError as e:
        typer.secho(f"Failed to set language '{lang}': {e}", fg="yellow", err=True)

    if is_ai_translated:
        track.track_name = "AI Translated"
        if verbose:
            typer.echo("Set track name to 'AI Translated'")

    return track


def perform_mux_operation(mkv: MKVFile, tmp_path: Path, mkv_path: Path, verbose: bool = False) -> None:
    if verbose:
        typer.echo("Starting mkvmerge operation...")
    mkv.mux(tmp_path)
    typer.secho(f"✓ Successfully muxed: {mkv_path.name}", fg="green")


def handle_file_operations(tmp: Path, output_path: Path, mkv_path: Path, verbose: bool = False) -> None:
    if tmp != output_path != mkv_path:
        if output_path.exists():
            output_path.unlink()
            if verbose:
                typer.echo("Removed existing output file")
        tmp.replace(output_path)
        if verbose:
            typer.echo("Moved to final output location")
    elif tmp != output_path:
        tmp.replace(mkv_path)
        if verbose:
            typer.echo("Replaced original file")


def mux_with_subtitle(
    mkv_path: Path,
    srt_path: Path,
    lang: str,
    output_path: Path,
    is_ai_translated: bool = False,
    ignore_mux_errors: bool = False,
    verbose: bool = False,
) -> None:
    typer.echo(f"Processing: {mkv_path.name} + {srt_path.name}")
    if verbose:
        typer.echo(f"Target language: {lang}, AI translated: {is_ai_translated}")
        typer.echo(f"Output: {output_path}")

    if output_path == mkv_path:
        with tempfile.NamedTemporaryFile(delete=False, dir=str(mkv_path.parent), suffix=".mkv") as f:
            tmp = Path(f.name)
        if verbose:
            typer.echo(f"Using temporary file: {tmp.name}")
    else:
        tmp = output_path
        if verbose:
            typer.echo("Writing directly to output")

    if verbose:
        typer.echo("Creating MKV file object and adding track")
    mkv = MKVFile(mkv_path)
    track = create_subtitle_track(srt_path, lang, is_ai_translated, verbose)
    mkv.add_track(track)

    try:
        perform_mux_operation(mkv, tmp, mkv_path, verbose)
    except Exception as e:
        if ignore_mux_errors:
            typer.secho(f"⚠ Mux error ignored for {mkv_path.name}: {e}", fg="yellow")
        else:
            typer.secho(f"✗ Mux failed for {mkv_path.name}: {e}", fg="red", err=True)
            raise

    handle_file_operations(tmp, output_path, mkv_path, verbose)
