"""Bounded image decoding shared by the dashboard and WhatsApp runtime."""
import base64
import io
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024


def image_data_url(data: bytes) -> str:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError('Gambar harus berukuran 1 byte–5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ('JPEG', 'PNG', 'WEBP'):
                    raise ValueError('Gunakan gambar JPEG, PNG, atau WebP.')
                if image.width * image.height > 20_000_000:
                    raise ValueError('Resolusi gambar maksimal 20 megapiksel.')
                image.load()
                normalized = ImageOps.exif_transpose(image).convert('RGB')
                normalized.thumbnail((1600, 1600))
                output = io.BytesIO()
                normalized.save(output, format='JPEG', quality=85)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError('Gambar rusak atau resolusinya terlalu besar.') from None
    return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode()


def decode_image(encoded: str) -> bytes:
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise ValueError('Data gambar tidak valid.') from None


def image_message(message, quoted=False):
    # View-once media deliberately remains private. Only ordinary images and
    # ephemeral wrappers are accepted; quoted images require an explicit command.
    for _ in range(3):
        if message.HasField('imageMessage'):
            return message
        if message.HasField('ephemeralMessage'):
            message = message.ephemeralMessage.message
        else:
            break
    if quoted:
        from legacy.utils import get_context_info
        context = get_context_info(message)
        if context is not None:
            return image_message(context.quotedMessage)
    return None
