from concurrent.futures import ThreadPoolExecutor, as_completed
from importlib.metadata import version
from pathlib import Path

import typer
from natsort import natsorted

from .ass_operations import convert_ass_to_srt
from .config import read_config
from .language_utils import has_language_in_set
from .mkv_operations import (
    compute_output_path,
    extract_subtitle_from_mkv,
    find_srt_file,
    find_subtitle_track_in_mkv,
    mux_with_subtitle,
    probe_subtitle_languages,
)
from .stats import (
    ProcessingStats,
    print_export_final_stats,
    print_final_stats,
    print_output_info,
    print_processing_info,
)

app = typer.Typer(add_completion=False)


def get_version() -> str:
    try:
        return version("mkv-submerge")
    except Exception:
        return "unknown"


def version_callback(value: bool) -> None:
    if value:
        app_version = get_version()
        typer.secho("🎬 ", nl=False, fg="bright_blue")
        typer.secho("mkv-submerge", nl=False, fg="bright_green", bold=True)
        typer.secho(" version ", nl=False)
        typer.secho(app_version, fg="bright_yellow", bold=True)
        raise typer.Exit()


def process_single_mkv_export(
    mkv: Path,
    language_priority: list[str],
    verbose: bool,
    dry_run: bool,
    stats: ProcessingStats,
) -> None:
    stats.total += 1
    if verbose:
        typer.echo(f"🔄 Processing file {stats.total}: {mkv.name}")

    for lang in language_priority:
        if verbose:
            typer.echo(f"🔍 Checking for existing {lang} subtitle file...")

        existing_srt = find_srt_file(mkv, lang, verbose)
        if existing_srt:
            if verbose:
                typer.echo(f"⏭️  Skipping {mkv.name}: {lang} subtitle already exists ({existing_srt.name})")
            stats.skipped_has_lang += 1
            return

        if verbose:
            typer.echo(f"🎬 Checking for {lang} subtitles inside MKV...")

        subtitle_track = find_subtitle_track_in_mkv(mkv, lang, verbose)
        if subtitle_track:
            if dry_run:
                codec = subtitle_track.track_codec or "unknown"
                track_language = subtitle_track.language or "unknown"
                typer.echo(
                    f"🎬 Would extract: {mkv.name} track {subtitle_track.track_id} "
                    f"({codec}) language:{track_language} with auto-detected format"
                )
                stats.processed += 1
                return

            extract_subtitle_from_mkv(subtitle_track, mkv, lang, verbose)
            stats.processed += 1
            return

    if verbose:
        typer.echo(f"⏭️  Skipping {mkv.name}: no suitable subtitles found for {language_priority}")
    stats.skipped_no_srt += 1


def process_single_mkv(
    mkv: Path,
    lang_check: str,
    lang_set: str,
    root: Path,
    output_dir: Path | None,
    ai_translated: bool,
    ignore_mux_errors: bool,
    verbose: bool,
    dry_run: bool,
    stats: ProcessingStats,
) -> None:
    stats.total += 1
    if verbose:
        typer.echo(f"🔄 Processing file {stats.total}: {mkv.name}")

    langs = probe_subtitle_languages(mkv, verbose)
    if has_language_in_set(lang_set, langs):
        if verbose:
            typer.echo(f"⏭️  Skipping {mkv.name}: already has {lang_set} subtitles")
        stats.skipped_has_lang += 1
        return

    srt = find_srt_file(mkv, lang_check, verbose)
    if not srt:
        if verbose:
            typer.echo(f"⏭️  Skipping {mkv.name}: no {lang_check} subtitle file found")
        stats.skipped_no_srt += 1
        return

    target = compute_output_path(mkv, root, output_dir)

    if dry_run:
        label = f"{lang_set} (AI Translated)" if ai_translated else lang_set
        typer.echo(f"🎬 Would add: {mkv.name} + {srt.name} as {label}")
        stats.processed += 1
        return

    mux_with_subtitle(mkv, srt, lang_set, target, ai_translated, ignore_mux_errors, verbose)
    stats.processed += 1


@app.command(help="Merge MKV files with external SRT subtitles")
def run(
    root: str | None = typer.Option(None, "--root", "-r", exists=True, file_okay=False, dir_okay=True),
    check_lang: str | None = typer.Option(
        None, "--check-lang", "-c", help="Language code for searching subtitle files (e.g., 'ru')"
    ),
    set_lang: str | None = typer.Option(
        None, "--set-lang", "-s", help="Language code to set in MKV file (e.g., 'rus')"
    ),
    output_dir: str | None = typer.Option(None, "--output-dir", "-o", dir_okay=True, file_okay=False),
    config: str | None = typer.Option(None, "--config"),
    ai_translated: bool = typer.Option(False, "--ai-translated", help="Mark subtitles as AI translated"),
    ignore_mux_errors: bool = typer.Option(False, "--ignore-mux-errors", help="Ignore errors during mux operations"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    workers: int = typer.Option(
        1, "--workers", "-w", min=1, max=8, help="Number of workers for concurrent processing (1-8)"
    ),
    _: bool = typer.Option(False, "--version", callback=version_callback, help="Show version and exit"),
) -> None:
    cfg = read_config(config)

    if not verbose:
        verbose_val = cfg.get("verbose", False)
        verbose = verbose_val if isinstance(verbose_val, bool) else False

    if verbose:
        typer.echo("🚀 Starting mkv-submerge application")
        typer.echo(f"📄 Configuration loaded from: {config}")

    if root is None and cfg.get("root"):
        root_val = cfg["root"]
        root = root_val if isinstance(root_val, str) else None
    if check_lang is None:
        check_lang_val = cfg.get("check_lang")
        check_lang = check_lang_val if isinstance(check_lang_val, str) else None
    if set_lang is None:
        set_lang_val = cfg.get("set_lang")
        set_lang = set_lang_val if isinstance(set_lang_val, str) else None
    if output_dir is None and cfg.get("output_dir"):
        output_dir_val = cfg["output_dir"]
        output_dir = output_dir_val if isinstance(output_dir_val, str) else None
    if not ai_translated:
        ai_translated_val = cfg.get("ai_translated", False)
        ai_translated = ai_translated_val if isinstance(ai_translated_val, bool) else False
    if not ignore_mux_errors:
        ignore_mux_errors_val = cfg.get("ignore_mux_errors", False)
        ignore_mux_errors = ignore_mux_errors_val if isinstance(ignore_mux_errors_val, bool) else False
    if workers == 1:
        workers_val = cfg.get("workers", 1)
        workers = workers_val if isinstance(workers_val, int) and 1 <= workers_val <= 8 else 1

    if root is None or check_lang is None:
        typer.echo("Must specify --root and --check-lang or config file.")
        raise typer.Exit(code=2)

    if set_lang is None:
        typer.echo("Must specify --set-lang for setting language in MKV file.")
        raise typer.Exit(code=2)

    root_path = Path(root)
    output_dir_path = Path(output_dir) if output_dir else None

    typer.echo(f"📁 Scanning directory: {root_path}")
    print_processing_info(check_lang, set_lang, ai_translated, ignore_mux_errors, verbose)
    print_output_info(output_dir)

    if output_dir_path is not None:
        output_dir_path.mkdir(parents=True, exist_ok=True)

    lang_check = check_lang.lower()
    lang_set = set_lang.lower()
    stats = ProcessingStats()

    mkv_files = list(natsorted(root_path.rglob("*.mkv")))
    typer.echo(f"📊 Found {len(mkv_files)} MKV files to scan")

    if workers == 1:
        for mkv in mkv_files:
            process_single_mkv(
                mkv=mkv,
                lang_check=lang_check,
                lang_set=lang_set,
                root=root_path,
                output_dir=output_dir_path,
                ai_translated=ai_translated,
                ignore_mux_errors=ignore_mux_errors,
                verbose=verbose,
                dry_run=dry_run,
                stats=stats,
            )
    else:
        typer.echo(f"🚀 Processing with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_mkv = {
                executor.submit(
                    process_single_mkv,
                    mkv=mkv,
                    lang_check=lang_check,
                    lang_set=lang_set,
                    root=root_path,
                    output_dir=output_dir_path,
                    ai_translated=ai_translated,
                    ignore_mux_errors=ignore_mux_errors,
                    verbose=verbose,
                    dry_run=dry_run,
                    stats=stats,
                ): mkv
                for mkv in mkv_files
            }

            for future in as_completed(future_to_mkv):
                mkv = future_to_mkv[future]
                try:
                    future.result()
                except Exception as exc:
                    typer.secho(f"✗ Error processing {mkv.name}: {exc}", fg="red", err=True)

    print_final_stats(stats)


@app.command(name="to-srt", help="Convert ASS files to SRT format")
def convert(
    root: str | None = typer.Option(None, "--root", "-r", exists=True, file_okay=False, dir_okay=True),
    config: str | None = typer.Option(None, "--config"),
    removing_effects: bool = typer.Option(False, "--removing-effects", help="Remove effects from the text"),
    remove_duplicates: bool = typer.Option(
        False, "--remove-duplicates", help="Remove and merge consecutive duplicate dialogues"
    ),
    cleanup: bool = typer.Option(False, "--cleanup", "-c", help="Delete ASS files after successful conversion"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    workers: int = typer.Option(
        1, "--workers", "-w", min=1, max=8, help="Number of workers for concurrent processing (1-8)"
    ),
) -> None:
    cfg = read_config(config)

    if not verbose:
        verbose_val = cfg.get("verbose", False)
        verbose = verbose_val if isinstance(verbose_val, bool) else False

    if verbose:
        typer.echo("🚀 Starting ASS to SRT conversion")
        typer.echo(f"📄 Configuration loaded from: {config}")

    if root is None and cfg.get("root"):
        root_val = cfg["root"]
        root = root_val if isinstance(root_val, str) else None

    if workers == 1:
        workers_val = cfg.get("workers", 1)
        workers = workers_val if isinstance(workers_val, int) and 1 <= workers_val <= 8 else 1

    if root is None:
        typer.echo("Must specify --root directory or config file.")
        raise typer.Exit(code=2)

    root_path = Path(root)

    typer.echo(f"📁 Scanning directory: {root_path}")

    if removing_effects:
        typer.echo("🎨 Will remove effects from text")
    if remove_duplicates:
        typer.echo("🔄 Will remove consecutive duplicate dialogues")
    if cleanup:
        typer.echo("🗑️  Will delete ASS files after successful conversion")

    stats = ProcessingStats()
    ass_files = list(natsorted(root_path.rglob("*.ass")))
    typer.echo(f"📊 Found {len(ass_files)} ASS files to convert")

    if workers == 1:
        for ass_file in ass_files:
            convert_ass_to_srt(
                ass_file=ass_file,
                removing_effects=removing_effects,
                remove_duplicates=remove_duplicates,
                cleanup=cleanup,
                verbose=verbose,
                dry_run=dry_run,
                stats=stats,
            )
    else:
        typer.echo(f"🚀 Processing with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_ass = {
                executor.submit(
                    convert_ass_to_srt,
                    ass_file=ass_file,
                    removing_effects=removing_effects,
                    remove_duplicates=remove_duplicates,
                    cleanup=cleanup,
                    verbose=verbose,
                    dry_run=dry_run,
                    stats=stats,
                ): ass_file
                for ass_file in ass_files
            }

            for future in as_completed(future_to_ass):
                ass_file = future_to_ass[future]
                try:
                    future.result()
                except Exception as exc:
                    typer.secho(f"✗ Error processing {ass_file.name}: {exc}", fg="red", err=True)

    print_final_stats(stats)


@app.command(help="Extract subtitles from MKV files to separate SRT files")
def export(
    root: str | None = typer.Option(None, "--root", "-r", exists=True, file_okay=False, dir_okay=True),
    languages: str | None = typer.Option(
        None, "--languages", "-l", help="Language priority order, comma-separated (e.g., 'ru,en,ja')"
    ),
    config: str | None = typer.Option(None, "--config"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    dry_run: bool = typer.Option(False, "--dry-run"),
    workers: int = typer.Option(
        1, "--workers", "-w", min=1, max=8, help="Number of workers for concurrent processing (1-8)"
    ),
) -> None:
    cfg = read_config(config)

    if not verbose:
        verbose_val = cfg.get("verbose", False)
        verbose = verbose_val if isinstance(verbose_val, bool) else False

    if verbose:
        typer.echo("🚀 Starting mkv-submerge export")
        typer.echo(f"📄 Configuration loaded from: {config}")

    if root is None and cfg.get("root"):
        root_val = cfg["root"]
        root = root_val if isinstance(root_val, str) else None

    if languages is None and cfg.get("languages"):
        languages_val = cfg["languages"]
        languages = languages_val if isinstance(languages_val, str) else None

    if workers == 1:
        workers_val = cfg.get("workers", 1)
        workers = workers_val if isinstance(workers_val, int) and 1 <= workers_val <= 8 else 1

    if root is None:
        typer.echo("Must specify --root directory or config file.")
        raise typer.Exit(code=2)

    if not languages:
        typer.echo("Must specify --languages priority order or config file.")
        raise typer.Exit(code=2)

    root_path = Path(root)
    language_priority = [lang.strip().lower() for lang in languages.split(",") if lang.strip()]

    if not language_priority:
        typer.echo("Invalid --languages format. Use comma-separated values like 'ru,en,ja'")
        raise typer.Exit(code=2)

    typer.echo(f"📁 Scanning directory: {root_path}")
    typer.echo(f"🌐 Language priority: {' → '.join(language_priority)}")

    stats = ProcessingStats()
    mkv_files = list(natsorted(root_path.rglob("*.mkv")))
    typer.echo(f"📊 Found {len(mkv_files)} MKV files to scan")

    if workers == 1:
        for mkv in mkv_files:
            process_single_mkv_export(
                mkv=mkv,
                language_priority=language_priority,
                verbose=verbose,
                dry_run=dry_run,
                stats=stats,
            )
    else:
        typer.echo(f"🚀 Processing with {workers} workers")

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_mkv = {
                executor.submit(
                    process_single_mkv_export,
                    mkv=mkv,
                    language_priority=language_priority,
                    verbose=verbose,
                    dry_run=dry_run,
                    stats=stats,
                ): mkv
                for mkv in mkv_files
            }

            for future in as_completed(future_to_mkv):
                mkv = future_to_mkv[future]
                try:
                    future.result()
                except Exception as exc:
                    typer.secho(f"✗ Error processing {mkv.name}: {exc}", fg="red", err=True)

    print_export_final_stats(stats)


def main() -> None:
    app()


if __name__ == "__main__":
    app()
