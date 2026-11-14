import os
import sys
import time
import ctypes
import logging
import logging.handlers
import xml.etree.ElementTree as ET
import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%d-%m-%Y %H:%M:%S'

# 1. Setup Logging to files in the same folder
# automation.log gets one short line per event - never exception text or tracebacks.
automation_log = logging.FileHandler(os.path.join(BASE_DIR, 'automation.log'), encoding='utf-8')
automation_log.setLevel(logging.INFO)
automation_log.addFilter(lambda record: record.name == 'root')  # keep library messages out
automation_log.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

# debug.log gets everything (request errors, tracebacks) and is capped in size.
debug_log = logging.handlers.RotatingFileHandler(
    os.path.join(BASE_DIR, 'debug.log'), maxBytes=512 * 1024, backupCount=1, encoding='utf-8'
)
debug_log.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s', DATE_FORMAT))

logging.basicConfig(level=logging.DEBUG, handlers=[automation_log, debug_log])

# 2. Load Environment Variables
load_dotenv()
CUSTOM_FOLDER = os.getenv("WALLPAPER_DIR", r"C:\Wallpapers")
FILE_NAME = "nasa_daily.jpg"
SAVE_PATH = os.path.join(CUSTOM_FOLDER, FILE_NAME)

# APOD now lives on science.nasa.gov. Both sources below are structured data
# published by that site, so nothing here depends on the page's HTML layout.
API_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic?per_page=1"
FEED_URL = "https://science.nasa.gov/feed/apod-basic/"

# Formats Windows can use as a wallpaper: JPEG, PNG, GIF, BMP
IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n", b"GIF87a", b"GIF89a", b"BM")


class UpdateError(Exception):
    """A failure whose message is short enough to be written to automation.log."""


def request_with_retry(url, retries=3, delay=5, **kwargs):
    """Performs a GET request, retrying if the network fails."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=(10, 30), **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                raise

def apod_from_api():
    """Latest APOD from the site's JSON endpoint."""
    data = request_with_retry(API_URL).json()
    entry = data[0] if isinstance(data, list) else data
    return {
        "date": entry.get("date"),
        "title": entry.get("title"),
        "media_type": entry["media_type"],
        "hdurl": entry.get("hdurl"),
    }

def apod_from_feed():
    """Latest APOD from the site's RSS feed (used when the JSON endpoint fails).

    The feed doesn't say whether an entry is a video, so it is treated as an
    image; on video days its hdurl is a still frame of the video.
    """
    item = ET.fromstring(request_with_retry(FEED_URL).content).find("./channel/item")
    return {
        "date": item.findtext("pubDate"),
        "title": item.findtext("title"),
        "media_type": "image",
        "hdurl": item.findtext("{*}hdurl"),
    }

def fetch_apod():
    """Returns today's APOD from the first source that gives a usable answer."""
    for source in (apod_from_api, apod_from_feed):
        try:
            data = source()
            logging.debug(f"{source.__name__} returned {data}")
            if data["media_type"] != "image" or data["hdurl"]:
                return data
        except Exception:
            logging.debug(f"{source.__name__} failed", exc_info=True)
    raise UpdateError("could not get today's APOD from NASA")

def download_image(url):
    """Downloads the image, rejecting anything that isn't actually an image."""
    try:
        response = request_with_retry(url)
    except requests.exceptions.RequestException as e:
        raise UpdateError("image download failed") from e

    img_data = response.content
    logging.debug(f"Downloaded {len(img_data)} bytes ({response.headers.get('Content-Type')}) from {response.url}")
    # NASA's redirects can answer an image URL with a web page and a 200 status
    if not img_data.startswith(IMAGE_SIGNATURES):
        raise UpdateError("NASA did not return a usable image")
    return img_data

def main():
    logging.debug("Run started")
    try:
        # Ensure directory exists
        if not os.path.exists(CUSTOM_FOLDER):
            os.makedirs(CUSTOM_FOLDER)
            logging.info(f"Created directory: {CUSTOM_FOLDER}")

        # Fetch data
        data = fetch_apod()

        # Verify media type
        if data.get("media_type") != "image":
            logging.info("Today's APOD is a video or article. Skipping wallpaper update.")
            return True

        # Download image
        logging.info("Downloading today's image...")
        img_data = download_image(data["hdurl"])

        # Write to a temp file first so a crash mid-download can't leave a corrupt wallpaper
        tmp_path = SAVE_PATH + ".tmp"
        with open(tmp_path, 'wb') as handler:
            handler.write(img_data)
        os.replace(tmp_path, SAVE_PATH)

        # Set wallpaper
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, SAVE_PATH, 3)
        if not result:
            raise UpdateError("Windows rejected the image")
        logging.info("Wallpaper updated successfully.")
        return True

    except Exception as e:
        reason = str(e) if isinstance(e, UpdateError) else "unexpected error"
        logging.debug("Run failed", exc_info=True)
        logging.error(f"Failed to update wallpaper: {reason}.")
        return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
