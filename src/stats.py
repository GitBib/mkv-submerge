from dataclasses import dataclass

import typer


@dataclass
class ProcessingStats:
    total: int = 0
    processed: int = 0
    skipped_has_lang: int = 0
    skipped_no_srt: int = 0


def print_final_stats(stats: ProcessingStats) -> None:
    typer.secho(
        f"✅ Processing completed: {stats.total} total, {stats.processed} processed, "
        f"{stats.skipped_has_lang} skipped (has language), {stats.skipped_no_srt} skipped (no SRT)",
        fg="cyan",
    )
    typer.echo(f"Scanned MKV: {stats.total}, processed: {stats.processed}")


def print_export_final_stats(stats: ProcessingStats) -> None:
    typer.secho(
        f"✅ Export completed: {stats.total} total, {stats.processed} exported, "
        f"{stats.skipped_has_lang} skipped (exists), {stats.skipped_no_srt} skipped (not found)",
        fg="cyan",
    )
    typer.echo(f"Scanned MKV: {stats.total}, exported subtitles: {stats.processed}")


def print_processing_info(
    check_lang: str, set_lang: str, ai_translated: bool, ignore_mux_errors: bool, verbose: bool
) -> None:
    typer.echo(f"🔍 Search language: {check_lang} → Set language: {set_lang}")

    if verbose:
        typer.echo(f"AI translated: {ai_translated}, Ignore mux errors: {ignore_mux_errors}")


def print_output_info(output_dir: str | None) -> None:
    if output_dir is not None:
        typer.echo(f"💾 Output directory: {output_dir}")
    else:
        typer.echo("💾 Output: overwriting original files")
