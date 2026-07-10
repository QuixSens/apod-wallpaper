# APOD Wallpaper

Automatically sets your Windows desktop wallpaper to NASA's [Astronomy Picture of the Day](https://apod.nasa.gov/apod/astropix.html) every morning.

## How it works

- [apod_wallpaper.py](apod_wallpaper.py) fetches today's APOD metadata from NASA's API, downloads the image (skipping days where the APOD is a video), and sets it as the desktop background via the Windows `SystemParametersInfoW` API.
- Failed network requests are retried with a short backoff.
- The image is written to a temp file and swapped in atomically, so a failed download never leaves a corrupt wallpaper in place.
- Runs are logged to `automation.log` in the project folder.
- A Windows Task Scheduler job runs the script silently (via `pythonw.exe`) every morning.

## Setup

1. Get a free API key from [api.nasa.gov](https://api.nasa.gov).
2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your API key and preferred wallpaper folder:
   ```
   NASA_API_KEY=your_key_here
   WALLPAPER_DIR=C:\Wallpapers
   ```
4. Create a Windows Task Scheduler task that runs `venv\Scripts\pythonw.exe apod_wallpaper.py` on a daily trigger (e.g. 9:00 AM).

## Notes

- `.env` holds your API key and is git-ignored — never commit it.
- `Image/` (downloaded wallpapers) and `automation.log` are also git-ignored since they're runtime output, not source.
