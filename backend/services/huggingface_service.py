import httpx

from config import HUGGINGFACE_API_KEY


HF_IMAGE_MODEL = (
    "black-forest-labs/FLUX.1-schnell"
)

API_URL = (
    f"https://router.huggingface.co/hf-inference/models/{HF_IMAGE_MODEL}"
)


async def generate_thumbnail(
    prompt: str,
    style_prompt: str,
    headshot_url: str,
) -> bytes:

    full_prompt = f"""
    {style_prompt}

    USER REQUEST:
    {prompt}

    IMPORTANT REQUIREMENTS:
    - Professional YouTube thumbnail
    - Cinematic lighting
    - High contrast
    - Viral YouTube style
    - Bold composition
    - Highly clickable
    - 1280x720 aspect ratio

    PERSON REFERENCE:
    Use the same person appearance from:
    {headshot_url}
    """

    headers = {
        "Authorization": f"Bearer {HUGGINGFACE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": full_prompt,
        "parameters": {
            "width": 1280,
            "height": 720,
        },
    }

    async with httpx.AsyncClient(timeout=120) as client:

        response = await client.post(
            API_URL,
            headers=headers,
            json=payload,
        )

        if response.status_code != 200:
            raise Exception(
                f"HuggingFace Error: "
                f"{response.status_code} - "
                f"{response.text}"
            )

        return response.content