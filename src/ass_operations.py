from pathlib import Path

import typer
from pyasstosrt import Subtitle

from .stats import ProcessingStats


def convert_ass_to_srt(
    ass_file: Path,
    removing_effects: bool,
    remove_duplicates: bool,
    cleanup: bool,
    verbose: bool,
    dry_run: bool,
    stats: ProcessingStats,
) -> None:
    stats.total += 1
    if verbose:
        typer.echo(f"🔄 Processing file {stats.total}: {ass_file.name}")

    srt_output = ass_file.with_suffix(".srt")

    if srt_output.exists():
        if verbose:
            typer.echo(f"⏭️  Skipping {ass_file.name}: SRT file already exists ({srt_output.name})")
        stats.skipped_has_lang += 1
        return

    if dry_run:
        typer.echo(f"🎬 Would convert: {ass_file.name} to {srt_output.name}")
        if cleanup:
            typer.echo(f"🗑️  Would delete: {ass_file.name} after conversion")
        stats.processed += 1
        return

    try:
        subtitle = Subtitle(filepath=ass_file, removing_effects=removing_effects, remove_duplicates=remove_duplicates)
        subtitle.convert()
        subtitle.export(str(srt_output.parent), encoding="utf-8")

        if verbose:
            typer.echo(f"✅ Converted: {ass_file.name} → {srt_output.name}")

        if cleanup:
            ass_file.unlink()
            if verbose:
                typer.echo(f"🗑️  Deleted: {ass_file.name}")

        stats.processed += 1
    except Exception as e:
        if verbose:
            typer.secho(f"✗ Error converting {ass_file.name}: {e}", fg="red", err=True)
        stats.skipped_no_srt += 1
