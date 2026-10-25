"""EXIF Metadata Extractor for Photos and Images.

Extracts original capture timestamps and camera device information from image files
using Pillow (PIL), allowing clean chronological and device-based photo sorting.
"""

from pathlib import Path
from typing import Optional, Dict, Tuple
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS


def get_image_exif_info(image_path: Path) -> Dict[str, Optional[str]]:
    """
    Extracts capture date and camera information from an image file.
    Returns: {
        'date_str': '2026:08:24 14:30:00',
        'year': '2026',
        'month': '08-August',
        'camera': 'Apple iPhone 15 Pro' or None
    }
    """
    result = {
        "date_str": None,
        "year": None,
        "month": None,
        "camera": None
    }

    if image_path.suffix.lower() not in [".jpg", ".jpeg", ".tiff", ".webp", ".png"]:
        return result

    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if not exif_data:
                return result

            named_tags = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, tag_id)
                named_tags[tag_name] = value

            # 1. Date extraction
            date_raw = (
                named_tags.get("DateTimeOriginal")
                or named_tags.get("DateTimeDigitized")
                or named_tags.get("DateTime")
            )

            if date_raw and isinstance(date_raw, str):
                try:
                    # Standard EXIF format: 'YYYY:MM:DD HH:MM:SS'
                    parts = date_raw.strip().split(" ")[0].split(":")
                    if len(parts) == 3 and len(parts[0]) == 4:
                        dt = datetime(int(parts[0]), int(parts[1]), int(parts[2]))
                        result["date_str"] = date_raw
                        result["year"] = dt.strftime("%Y")
                        result["month"] = dt.strftime("%m-%B")
                except Exception:
                    pass

            # 2. Camera extraction
            make = named_tags.get("Make")
            model = named_tags.get("Model")
            if model and isinstance(model, str):
                camera_str = f"{make} {model}".strip() if make and make not in model else model.strip()
                result["camera"] = camera_str

    except Exception:
        # Gracefully handle corrupt or non-exif images
        pass

    return result


def get_exif_destination_subfolder(image_path: Path) -> Optional[str]:
    """
    Returns structured photo path like 'Media/Pictures/2026/08-August'
    if EXIF date is found, else None.
    """
    info = get_image_exif_info(image_path)
    if info["year"] and info["month"]:
        return f"Media/Pictures/{info['year']}/{info['month']}"
    return None
