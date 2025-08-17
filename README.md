# 🎬 mkv-submerge

A powerful CLI tool for batch processing MKV video files that automatically detects missing subtitle tracks and merges matching SRT subtitle files using MKVToolNix. Features smart SRT-to-MKV matching, language detection, dry-run mode, and support for AI-translated subtitle marking.

## ✨ Features

- 🔍 **Smart subtitle detection** - Automatically finds matching SRT files for MKV videos
- 🌐 **Language awareness** - Checks existing subtitle languages and skips files that already have the target language
- 📁 **Flexible file matching** - Supports exact matches and pattern-based SRT discovery
- 🤖 **AI translation support** - Mark subtitles as AI-translated with metadata
- 🛡️ **Error handling** - Continue processing even if some files fail
- 🏃 **Dry-run mode** - Preview what would be processed without making changes
- ⚙️ **Configuration files** - Save settings in TOML config files for reuse
- 📊 **Progress tracking** - Detailed statistics and verbose output options

## 🚀 Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management:

```bash
uv sync
```

**Requirements:**
- Python 3.12+
- [MKVToolNix](https://mkvtoolnix.download/) (`mkvmerge` must be in PATH)

## 📖 Usage

### Basic Usage

```bash
mkv-submerge \
  --root "/path/to/video/files" \
  --check-lang ru \
  --set-lang rus
```

### Advanced Example

```bash
mkv-submerge \
  --root "/path/to/video/files" \
  --check-lang ru \
  --set-lang rus \
  --output-dir "/path/to/output" \
  --ai-translated \
  --ignore-mux-errors \
  --verbose
```

### Options

| Option | Short | Description | Required |
|--------|-------|-------------|----------|
| `--root` | `-r` | Root directory containing MKV files | ✅ |
| `--check-lang` | `-c` | Language code for searching SRT files (e.g., 'ru') | ✅ |
| `--set-lang` | `-s` | Language code to set in MKV file (e.g., 'rus') | ✅ |
| `--output-dir` | `-o` | Output directory (overwrites originals if not specified) | ❌ |
| `--config` | | Path to TOML configuration file | ❌ |
| `--ai-translated` | | Mark subtitles as AI translated | ❌ |
| `--ignore-mux-errors` | | Continue processing on mkvmerge errors | ❌ |
| `--verbose` | `-v` | Verbose output with detailed progress | ❌ |
| `--dry-run` | | Preview mode - show what would be processed | ❌ |
| `--version` | | Show version information | ❌ |

## ⚙️ Configuration File

Create a TOML configuration file to save your settings:

```toml
[mkv_submerge]
root = "/path/to/video/files"
check_lang = "ru"
set_lang = "rus"
output_dir = "/path/to/output"
ai_translated = true
ignore_mux_errors = true
verbose = false
```

Usage with config file:
```bash
mkv-submerge --config config.toml
```

## 🔍 How It Works

1. **Scan Directory**: Recursively finds all `.mkv` files in the specified root directory
2. **Check Existing Subtitles**: Uses MKVToolNix to probe existing subtitle languages
3. **Skip or Process**: Skips files that already have the target language
4. **Find SRT Files**: Looks for matching `.srt` files using smart patterns:
   - Exact match: `movie.ru.srt` for `movie.mkv`
   - Pattern match: `movie.SOMETHING.ru.srt` for `movie.mkv`
5. **Merge Subtitles**: Uses `mkvmerge` to add subtitle tracks with proper language metadata
6. **Statistics**: Reports processing results and any skipped files

## 🧪 Testing

Preview what would be processed without making changes:

```bash
mkv-submerge \
  --root "/path/to/videos" \
  --check-lang ru \
  --set-lang rus \
  --verbose \
  --dry-run
```

## 🎯 Version

Check the current version:

```bash
mkv-submerge --version
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
