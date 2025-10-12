import shutil
import tempfile
from pathlib import Path

import typer
from natsort import natsorted
from pymkv import MKVFile, MKVTrack

from .language_utils import is_language_match

CODEC_TO_EXTENSION = {
    "S_TEXT/UTF8": ".srt",
    "S_TEXT/ASS": ".ass",
    "S_TEXT/SSA": ".ssa",
    "S_TEXT/WEBVTT": ".vtt",
    "S_HDMV/PGS": ".sup",
    "S_DVBSUB": ".sub",
    "S_VOBSUB": ".sub",
    "S_TEXT/USF": ".usf",
    "S_KATE": ".kate",
    "SubStationAlpha": ".ass",
    "SubRip/SRT": ".srt",
    "WEBVTT": ".vtt",
    "HDMV PGS": ".sup",
    "DVB subtitles": ".sub",
    "VobSub": ".sub",
}

SUBTITLE_EXTENSIONS = [".srt", ".ass", ".ssa", ".vtt", ".sup", ".sub", ".usf", ".kate"]


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

    stem = mkv_path.with_suffix("").name

    for ext in SUBTITLE_EXTENSIONS:
        exact = mkv_path.with_suffix(f".{lang}{ext}")
        if exact.exists():
            if verbose:
                typer.echo(f"Found exact match: {exact.name}")
            return exact

        pattern = f"{stem}.*.{lang}{ext}"
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
        try:
            tmp.replace(output_path)
        except OSError:
            shutil.move(str(tmp), str(output_path))
        if verbose:
            typer.echo("Moved to final output location")
    elif tmp != output_path:
        try:
            tmp.replace(mkv_path)
        except OSError:
            shutil.move(str(tmp), str(mkv_path))
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
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mkv") as f:
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


def find_subtitle_track_in_mkv(mkv_path: Path, lang: str, verbose: bool = False) -> MKVTrack | None:
    if verbose:
        typer.echo(f"Searching for {lang} subtitles inside: {mkv_path}")

    try:
        mkv = MKVFile(mkv_path)

        for track in mkv.tracks:
            if track.track_type != "subtitles":
                continue

            track_lang = track.language
            track_id = track.track_id

            if verbose:
                typer.echo(f"Found subtitle track {track_id}: language={track_lang}")

            if is_language_match(lang, track_lang):
                if verbose:
                    typer.echo(f"Match found! Track {track_id} language '{track_lang}' matches requested '{lang}'")
                return track

        if verbose:
            typer.echo(f"No {lang} subtitle track found in {mkv_path.name}")
        return None

    except Exception as e:
        typer.secho(f"Failed to probe subtitle tracks in {mkv_path}: {e}", fg="yellow", err=True)
        return None


def extract_subtitle_from_mkv(track: MKVTrack, mkv_path: Path, lang: str, verbose: bool = False) -> None:
    if verbose:
        typer.echo(f"Extracting subtitle track {track.track_id} ({track.track_codec}) for language {lang}")

    try:
        codec = track.track_codec
        extension = CODEC_TO_EXTENSION.get(codec, ".srt")

        mkv_stem = mkv_path.stem
        final_path = mkv_path.parent / f"{mkv_stem}.{lang}{extension}"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_output = Path(temp_dir)

            if verbose:
                typer.echo(f"Using codec '{codec}' -> '{extension}'")
                typer.echo(f"Temporary directory: {temp_output}")
                typer.echo(f"Target file: {final_path.name}")

            extracted_path = track.extract(output_path=str(temp_output), silent=not verbose)
            extracted_file = Path(extracted_path)

            if verbose:
                typer.echo(f"Track extracted to: {extracted_file}")

            if extracted_file.exists():
                try:
                    final_path.parent.mkdir(parents=True, exist_ok=True)
                    if final_path.exists():
                        final_path.unlink()
                    try:
                        shutil.copy2(str(extracted_file), str(final_path))
                    except OSError:
                        shutil.move(str(extracted_file), str(final_path))
                    if verbose:
                        typer.echo(f"Copied: {extracted_file.name} → {final_path.name}")
                    typer.secho(f"✓ Successfully extracted subtitle: {final_path.name}", fg="green")

                except Exception as rename_error:
                    if verbose:
                        typer.echo(f"Copy failed: {rename_error}")
                    typer.secho(f"✗ Failed to save extracted subtitle: {rename_error}", fg="red", err=True)
            else:
                typer.secho("✗ Extraction failed: temporary file not created", fg="red", err=True)

    except Exception as e:
        typer.secho(f"✗ Extraction failed for track {track.track_id}: {e}", fg="red", err=True)
