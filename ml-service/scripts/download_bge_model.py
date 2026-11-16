"""
Download script for BAAI/bge-small-en-v1.5 ONNX model artifacts from Hugging Face.
Artifacts:
- model.onnx (~133 MB)
- tokenizer.json (~711 KB)
- config.json (~743 B)
"""
import os
import sys
import hashlib
import urllib.request

MODEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app", "models", "bge-small-en-v1.5"))

FILES_TO_DOWNLOAD = [
    {
        "filename": "model.onnx",
        "url": "https://huggingface.co/BAAI/bge-small-en-v1.5/resolve/main/onnx/model.onnx",
        "min_size": 120 * 1024 * 1024,  # ~133 MB (126.9 MiB)
    },
    {
        "filename": "tokenizer.json",
        "url": "https://huggingface.co/BAAI/bge-small-en-v1.5/raw/main/tokenizer.json",
        "min_size": 650 * 1024,  # ~711 KB
    },
    {
        "filename": "config.json",
        "url": "https://huggingface.co/BAAI/bge-small-en-v1.5/raw/main/config.json",
        "min_size": 500,  # ~743 B
    }
]

def download_file(url: str, dest_path: str):
    print(f"Downloading {url} -> {dest_path}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "JuristAI-ModelDownloader/1.0"}
    )
    with urllib.request.urlopen(req, timeout=120) as response, open(dest_path, "wb") as out_file:
        total_size = int(response.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024  # 1MB
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"\r  {downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB ({percent:.1f}%)", end="", flush=True)
            else:
                print(f"\r  {downloaded / (1024*1024):.1f} MB", end="", flush=True)
    print()

def compute_sha256(file_path: str) -> str:
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    print(f"Target directory: {MODEL_DIR}")
    
    for item in FILES_TO_DOWNLOAD:
        dest = os.path.join(MODEL_DIR, item["filename"])
        if os.path.exists(dest) and os.path.getsize(dest) >= item["min_size"]:
            print(f"[ALREADY EXISTS] {item['filename']} ({os.path.getsize(dest)} bytes)")
        else:
            download_file(item["url"], dest)
            size = os.path.getsize(dest)
            if size < item["min_size"]:
                raise RuntimeError(f"Downloaded file {item['filename']} size {size} is smaller than expected min_size {item['min_size']}")
        
        sha = compute_sha256(dest)
        print(f"  {item['filename']}: Size = {os.path.getsize(dest):,} bytes | SHA-256 = {sha}")

    print("\nAll BGE-small-en-v1.5 model artifacts successfully verified.")

if __name__ == "__main__":
    main()
