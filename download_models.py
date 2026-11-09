#!/usr/bin/env python3
"""
IntruderLens — Model Downloader
Downloads the required OpenCV ONNX models for face detection (YuNet) and
face recognition (SFace) from the official OpenCV Zoo repository.

Run this once after cloning:
    python download_models.py
"""

import urllib.request
import hashlib
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent / "models"

MODELS = [
    {
        "name": "face_detection_yunet_2023mar.onnx",
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "size_kb": 227,
        "description": "YuNet — Lightweight real-time CNN face detector (OpenCV)"
    },
    {
        "name": "face_recognition_sface_2021dec.onnx",
        "url": "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "size_kb": 37789,
        "description": "SFace — High-accuracy face recognition / embedding model (OpenCV)"
    }
]


def download_model(url: str, dest: Path, label: str, expected_size_kb: int):
    if dest.exists():
        actual_kb = dest.stat().st_size // 1024
        print(f"  [SKIP] '{dest.name}' already exists ({actual_kb} KB)")
        return True

    print(f"  [DOWNLOADING] {label}")
    print(f"    URL: {url}")
    print(f"    Expected size: ~{expected_size_kb} KB")

    try:
        def reporthook(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, downloaded * 100 // total_size)
                bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                print(f"\r    [{bar}] {pct}% ({downloaded // 1024} KB)", end="", flush=True)

        urllib.request.urlretrieve(url, dest, reporthook)
        print()
        actual_kb = dest.stat().st_size // 1024
        print(f"  [OK] Saved to {dest} ({actual_kb} KB)\n")
        return True
    except Exception as e:
        print(f"\n  [ERROR] Failed to download {dest.name}: {e}")
        return False


def main():
    print("=" * 60)
    print("  IntruderLens — Model Downloader")
    print("=" * 60)
    print(f"\nModels will be saved to: {MODELS_DIR}\n")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    all_ok = True
    for model in MODELS:
        dest = MODELS_DIR / model["name"]
        ok = download_model(model["url"], dest, model["description"], model["size_kb"])
        if not ok:
            all_ok = False

    print("=" * 60)
    if all_ok:
        print("  ✅ All models ready. IntruderLens face recognition is set up!")
    else:
        print("  ❌ Some models failed to download. Check your internet connection and try again.")
    print("=" * 60)


if __name__ == "__main__":
    main()

