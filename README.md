# APOD Wallpaper

Automatically sets your Windows desktop wallpaper to NASA's [Astronomy Picture of the Day](https://science.nasa.gov/apod/) every morning.

## How it works

- [apod_wallpaper.py](apod_wallpaper.py) fetches today's APOD metadata from science.nasa.gov, downloads the image (skipping days where the APOD is a video), and sets it as the desktop background via the Windows `SystemParametersInfoW` API.
- The metadata comes from the site's JSON endpoint (`/wp-json/wp/v2/apod-basic`), falling back to its RSS feed (`/feed/apod-basic/`) if that fails. No API key is needed. The feed doesn't flag video days, so on the fallback path a video day uses NASA's still frame instead of being skipped.
- Failed network requests are retried with a short backoff.
- The download is checked to be a real image, then written to a temp file and swapped in atomically, so a failed download never leaves a corrupt wallpaper in place.
- A Windows Task Scheduler job runs the script silently (via `pythonw.exe`) every morning.

## Logs

- `automation.log` has one or two short lines per run. A failed run adds a single line such as `Failed to update wallpaper: image download failed.`
- `debug.log` has the details behind a failure (URLs, HTTP errors, tracebacks). It is capped at about 512 KB plus one backup (`debug.log.1`).
- The script exits with code 1 when a run fails, which shows up as the task's "Last Run Result" in Task Scheduler.

## Setup

1. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set your preferred wallpaper folder:
   ```
   WALLPAPER_DIR=C:\Wallpapers
   ```
3. Create a Windows Task Scheduler task that runs `venv\Scripts\pythonw.exe apod_wallpaper.py` on a daily trigger (e.g. 9:00 AM). On a laptop, untick "Start the task only if the computer is on AC power" under Conditions, or the task is skipped on battery.

## Notes

- `.env` is git-ignored.
- `Image/` (downloaded wallpapers), `automation.log` and `debug.log` are also git-ignored since they're runtime output, not source.
