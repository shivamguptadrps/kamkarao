"""Shrink every uploaded photo so pages stay fast on cheap phones."""
from io import BytesIO
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps


def optimize_image(field, max_width=800, quality=78):
    """Resize a freshly uploaded image to WebP in place. Already-saved files are left alone."""
    if not field or getattr(field, "_committed", True):
        return
    try:
        field.file.seek(0)
        img = Image.open(field.file)
        img = ImageOps.exif_transpose(img)
    except Exception:
        return  # not an image Pillow understands; keep the original
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, round(img.height * ratio)), Image.LANCZOS)
    out = BytesIO()
    img.save(out, "WEBP", quality=quality, method=5)
    name = Path(field.name).stem + ".webp"
    field.save(name, ContentFile(out.getvalue()), save=False)
