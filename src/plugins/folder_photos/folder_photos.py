"""Display randomly chosen photos from a local folder or synchronized NAS cache."""

import logging
import os
from pathlib import Path
import random

from PIL import Image, ImageOps
from plugins.base_plugin.base_plugin import BasePlugin

logger = logging.getLogger(__name__)
PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}
DEFAULT_FOLDER = "/var/lib/inkypi-photos"


def discover_photos(folder, recursive=True):
    """Skip hidden uploads, symlinks, companion videos, and empty files."""
    root = Path(folder).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise RuntimeError("Photo folder is unavailable. Choose an existing absolute folder path.")
    photos = []

    def scan_error(error):
        raise RuntimeError("Photo folder could not be read. Check its permissions.") from error

    for directory, subdirs, filenames in os.walk(root, followlinks=False, onerror=scan_error):
        subdirs[:] = sorted(
            name for name in subdirs
            if not name.startswith(".") and not (Path(directory) / name).is_symlink()
        ) if recursive else []
        for name in sorted(filenames):
            path = Path(directory) / name
            if name.startswith(".") or path.suffix.lower() not in PHOTO_EXTENSIONS or path.is_symlink():
                continue
            try:
                if path.is_file() and path.stat().st_size > 0:
                    photos.append(path)
            except OSError:
                # A sync can rename/remove a file between directory listing and stat.
                continue
    return photos


class FolderPhotos(BasePlugin):
    def generate_image(self, settings, device_config):
        folder = str(settings.get("folderPath") or DEFAULT_FOLDER).strip()
        recursive = settings.get("includeSubfolders", "true") in (True, "true")
        photos = discover_photos(folder, recursive)
        if not photos:
            raise RuntimeError("No photos found yet. Add photos to the shared folder and allow sync to finish.")

        # Keep selection state per playlist instance, not on the shared plugin object.
        previous = settings.get("last_photo")
        candidates = [path for path in photos if str(path) != previous]
        random.shuffle(candidates)
        candidates.extend(path for path in photos if str(path) == previous)

        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        fit = settings.get("fitMode", "contain")
        if fit not in ("contain", "crop"):
            raise RuntimeError("Choose Fit whole photo or Fill screen for the photo layout.")

        for path in candidates:
            try:
                # Determine a bounded decode size for contain mode before loading.
                # Reuse InkyPi's adaptive loader for JPEG draft decoding and EXIF rotation.
                with Image.open(path) as header:
                    width, height = header.size
                    if header.getexif().get(274) in (5, 6, 7, 8):
                        width, height = height, width
                if fit == "contain":
                    scale = min(dimensions[0] / width, dimensions[1] / height)
                    load_dimensions = (
                        max(1, min(dimensions[0], round(width * scale))),
                        max(1, min(dimensions[1], round(height * scale))),
                    )
                else:
                    load_dimensions = dimensions
                image = self.image_loader.from_file(str(path), load_dimensions, resize=True)
                if image is None:
                    continue
                image = image.convert("RGB")
                if fit == "contain":
                    result = ImageOps.pad(image, dimensions, color="white", method=Image.Resampling.LANCZOS)
                else:
                    result = image
                settings["last_photo"] = str(path)
                logger.info("Folder Photos selected %s", path.name)
                return result
            except (OSError, ValueError, Image.DecompressionBombError):
                logger.warning("Skipping unreadable photo: %s", path.name, exc_info=True)
        raise RuntimeError("None of the photos could be opened. Check file formats and upload completion.")

    # Inherit the no-op cleanup: removing a playlist must never delete source/cache photos.
