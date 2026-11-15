def is_valid_video_header(chunk: bytes) -> bool:
    """
    Validate that file begins with valid video magic bytes:
    - MP4 / MOV: 'ftyp' at offset 4 (e.g. ftypisom, ftypmp42, etc.)
    - WebM / MKV: Matroska/EBML header \x1a\x45\xdf\xa3
    """
    if len(chunk) < 8:
        return False

    # Check EBML / WebM / MKV
    if chunk.startswith(b"\x1a\x45\xdf\xa3"):
        return True

    # Check MP4 / MOV / QuickTime: 4 bytes box size + 'ftyp'
    if len(chunk) >= 12 and chunk[4:8] == b"ftyp":
        return True

    return False


def is_valid_image_header(chunk: bytes) -> bool:
    """
    Validate that file begins with valid image magic bytes:
    - JPEG: \xff\xd8\xff
    - PNG: \x89PNG\r\n\x1a\n
    - WebP: RIFF....WEBP
    """
    if len(chunk) < 4:
        return False

    # JPEG
    if chunk.startswith(b"\xff\xd8\xff"):
        return True

    # PNG
    if chunk.startswith(b"\x89PNG\r\n\x1a\n"):
        return True

    # WebP: 'RIFF' + 4 bytes size + 'WEBP'
    if len(chunk) >= 12 and chunk.startswith(b"RIFF") and chunk[8:12] == b"WEBP":
        return True

    return False
