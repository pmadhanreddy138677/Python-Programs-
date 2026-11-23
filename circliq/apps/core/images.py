"""Uploaded-image hardening: verify, strip metadata (EXIF/GPS), bound the size, re-encode, and give the file an unguessable name."""
import uuid
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image, ImageOps

MAX_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # decompression-bomb guard
FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp")}


def sanitize_image(f, max_side=2000):
    try:
        f.seek(0)
        probe = Image.open(f)
        fmt = probe.format
        probe.verify()
        f.seek(0)
        img = Image.open(f)
        img.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError("That image is too large.")
    except Exception:
        raise ValidationError("We couldn't read that image. Use a valid JPG, PNG or WebP file.")
    if fmt not in FORMATS:
        raise ValidationError("Use a JPG, PNG or WebP image.")
    img = ImageOps.exif_transpose(img)  # honour orientation, then drop all metadata on save
    img.thumbnail((max_side, max_side))
    ext, mime = FORMATS[fmt]
    out = BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(out, "JPEG", quality=85, optimize=True)
    elif fmt == "PNG":
        img.save(out, "PNG", optimize=True)
    else:
        img.save(out, "WEBP", quality=85)
    size = out.tell()
    out.seek(0)
    return InMemoryUploadedFile(out, getattr(f, "field_name", None), f"{uuid.uuid4().hex}.{ext}", mime, size, None)
