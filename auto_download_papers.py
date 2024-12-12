import os
import re
import requests
import time
from tqdm import tqdm
from urllib.parse import urlparse

# Constants
BASE_API_URL = "https://dblp.org/search/publ/api"
QUERY = "ICLR+2024"
MAX_RESULTS = 1000  # Maximum results per request
OUTPUT_DIR = f"/data/lyc/papers/{QUERY.replace('+', '_')}/pdf"
USE_SINGLE_THREAD = False  # 是否使用单线程运行
THREAD_COUNT = 8  # 多线程模式下的线程数
API_CALL_INTERVAL = 2  # 调用 API 的时间间隔（秒）
DOWNLOAD_INTERVAL = 1  # 单线程模式下每次下载之间的间隔（秒）

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 下载统计
success_count = 0
failure_count = 0


def sanitize_filename(filename):
    """Sanitize filename to replace special characters with underscores."""
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def fetch_papers(start_index):
    """
    Fetch papers from the API starting at a specific index.
    Returns a list of papers.
    """
    try:
        params = {
            "q": QUERY,
            "format": "json",
            "h": MAX_RESULTS,
            "f": start_index
        }
        response = requests.get(BASE_API_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        hits = data.get("result", {}).get("hits", {}).get("hit", [])
        return hits
    except Exception as e:
        print(f"Error fetching papers at index {start_index}: {e}")
        return []


def download_pdf(paper_info):
    """
    Download a single paper's PDF using the `ee` link.
    """
    global success_count, failure_count

    try:
        info = paper_info.get("info", {})
        title = info.get("title", "Unknown_Title")
        paper_type = info.get("type", "")
        ee = info.get("ee", "")

        # Skip papers that are not "Conference and Workshop Papers"
        if paper_type != "Conference and Workshop Papers" or not ee:
            return

        # Construct the PDF URL
        parsed_url = urlparse(ee)
        if "openreview.net" not in parsed_url.netloc:
            return
        pdf_url = ee.replace("/forum?id=", "/pdf?id=")

        # Sanitize the title for the filename
        sanitized_title = sanitize_filename(title)
        filename = os.path.join(OUTPUT_DIR, f"{sanitized_title}.pdf")

        # Skip if the file already exists
        if os.path.exists(filename):
            success_count += 1
            return

        # Download the PDF
        response = requests.get(pdf_url, timeout=15)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Save the PDF
        with open(filename, "wb") as f:
            f.write(response.content)

        # Update success count
        success_count += 1

    except Exception as e:
        # Update failure count
        failure_count += 1
        print(f"Error downloading paper '{paper_info.get('info', {}).get('title', 'Unknown')}' : {e}")


def main():
    global success_count, failure_count

    # Fetch all papers
    print("Fetching paper metadata...")
    all_papers = []
    start_index = 0

    while True:
        papers = fetch_papers(start_index)
        if not papers:
            break
        all_papers.extend(papers)
        start_index += MAX_RESULTS
        print(f"Fetched {len(papers)} papers, total so far: {len(all_papers)}")

        # If the number of papers fetched is less than MAX_RESULTS, we've reached the end
        if len(papers) < MAX_RESULTS:
            break

        # Add delay between API calls
        time.sleep(API_CALL_INTERVAL)

    print(f"Total papers fetched: {len(all_papers)}")

    # Initialize progress bar
    progress_bar = tqdm(total=len(all_papers), desc="Downloading PDFs", unit="file")

    if USE_SINGLE_THREAD:
        # Single-threaded mode
        print("Running in single-threaded mode...")
        for paper in all_papers:
            download_pdf(paper)
            progress_bar.update(1)
            progress_bar.set_postfix(Success=success_count, Failed=failure_count)
            time.sleep(DOWNLOAD_INTERVAL)  # Add delay between downloads
    else:
        # Multi-threaded mode
        print("Running in multi-threaded mode...")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
            futures = [executor.submit(download_pdf, paper) for paper in all_papers]
            for future in as_completed(futures):
                progress_bar.update(1)
                progress_bar.set_postfix(Success=success_count, Failed=failure_count)

    progress_bar.close()

    # Print final statistics
    print(f"Download completed. Total: {len(all_papers)}, Success: {success_count}, Failed: {failure_count}")


if __name__ == "__main__":
    main()
