# Canvas Video Downloader

Download batches of Panopto lesson videos through their available Download buttons in Penn Canvas. Sign in through a browser window; no Canvas API token is required.

This version supports **Penn Canvas course 1942808**. It is an independent utility, not an official Penn, Canvas, or Panopto product.

## Get started

Download `canvas_videos.py` and follow [the setup instructions](INSTRUCTIONS.md). Requires Python 3.9 or newer. The commands below are for macOS/Linux:

```sh
python3 -m venv .video-venv
source .video-venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python canvas_videos.py --start "YOUR_CANVAS_LESSON_URL" --count 8 --workers 3
```

Complete sign-in in the browser that opens, wait for the lesson video to appear, then press Enter in Terminal.

## How batches work

- `--count 8` checks eight consecutive course items, including the starting lesson. Non-video items count toward this total.
- `--workers 3` downloads up to three videos concurrently.
- Files are saved under `canvas_videos/` in your current directory.
- Completed downloads are skipped on subsequent runs.
- `--urls lessons.txt` selects specific lesson URLs, one per line, instead of following consecutive course items.
- `--dry-run` lists the batch without downloading.

Use `python canvas_videos.py --help` for all options.

## Scope and limitations

Only videos with an enabled Panopto Download button are downloaded. The script does not export interactive quizzes or bypass access restrictions. It opens a separate browser session and does not save authentication state between runs.

The starting lesson's Download button was inspected while signed in. Syntax, command-line handling, URL validation, and filename checks passed locally. A complete download run through the script has not yet been verified.

Downloaded videos, credentials, and browser profiles do not belong in this repository. Use downloaded course materials according to your course's sharing rules.
