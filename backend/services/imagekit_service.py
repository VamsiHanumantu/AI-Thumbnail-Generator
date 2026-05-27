from imagekitio import ImageKit
from config import IMAGEKIT_PRIVATE_KEY


imagekit = ImageKit(
    private_key=IMAGEKIT_PRIVATE_KEY
)


def upload_file(
    filebytes: bytes,
    filename: str,
    folder: str,
    content_type: str = "image/jpeg",
) -> str:

    result = imagekit.files.upload(
        file=(filename, filebytes, content_type),
        file_name=filename,
        folder=folder,
        use_unique_file_name=True,
        is_private_file=False,
    )

    return result.url


def get_variants(base_url: str) -> dict:
    return {
        "youtube": f"{base_url}?tr=w-1280,h-720,c-maintain_ratio,fo-auto",
        "shorts": f"{base_url}?tr=w-1080,h-1920,c-maintain_ratio,fo-auto",
        "square": f"{base_url}?tr=w-1080,h-1080,c-maintain_ratio,fo-auto",
    }