import os
import requests
import zipfile
import tempfile
import sys

def download_dataset(download_url, output_dir):
    print(f"Downloading dataset from {download_url}...")
    response = requests.get(download_url, stream=True)
    if response.status_code != 200:
        print(f"Failed to download dataset. Status code: {response.status_code}")
        sys.exit(1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp_file:
        for chunk in response.iter_content(chunk_size=8192):
            tmp_file.write(chunk)
        tmp_filepath = tmp_file.name

    print(f"Unzipping dataset to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(tmp_filepath, 'r') as zip_ref:
        zip_ref.extractall(output_dir)
    
    os.remove(tmp_filepath)
    print("Download and extraction complete.")

if __name__ == "__main__":
    # URL for the Figshare dataset (dataset.zip)
    URL = "https://ndownloader.figshare.com/files/37502683"
    OUTPUT_DIR = "data/raw"
    download_dataset(URL, OUTPUT_DIR)
