import os
import time
import ctypes
import logging
import requests
from dotenv import load_dotenv

# 1. Setup Logging to a file in the same folder
logging.basicConfig(
    filename=os.path.join(os.path.dirname(__file__), 'automation.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S'
)

# 2. Load Environment Variables
load_dotenv()
API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
CUSTOM_FOLDER = os.getenv("WALLPAPER_DIR", r"C:\Wallpapers")
FILE_NAME = "nasa_daily.jpg"
SAVE_PATH = os.path.join(CUSTOM_FOLDER, FILE_NAME)

URL = f"https://api.nasa.gov/planetary/apod?api_key={API_KEY}"

def request_with_retry(url, retries=3, delay=5, **kwargs):
    """Performs a GET request, retrying if the network fails."""
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
            else:
                logging.error("All retry attempts failed due to network errors.")
                raise

def main():
    # Ensure directory exists
    if not os.path.exists(CUSTOM_FOLDER):
        os.makedirs(CUSTOM_FOLDER)
        logging.info(f"Created directory: {CUSTOM_FOLDER}")

    try:
        # Fetch data
        data = request_with_retry(URL).json()

        # Verify media type
        if data.get("media_type") != "image":
            logging.info("Today's APOD is a video or article. Skipping wallpaper update.")
            return

        image_url = data.get("hdurl", data.get("url"))

        # Download image
        logging.info("Downloading today's image...")
        img_data = request_with_retry(image_url).content

        # Write to a temp file first so a crash mid-download can't leave a corrupt wallpaper
        tmp_path = SAVE_PATH + ".tmp"
        with open(tmp_path, 'wb') as handler:
            handler.write(img_data)
        os.replace(tmp_path, SAVE_PATH)

        # Set wallpaper
        result = ctypes.windll.user32.SystemParametersInfoW(20, 0, SAVE_PATH, 3)
        if result:
            logging.info("Wallpaper updated successfully.")
        else:
            logging.error("SystemParametersInfoW failed to set the wallpaper.")

    except Exception as e:
        logging.critical(f"Automation failed: {e}", exc_info=True)

if __name__ == "__main__":
    main()