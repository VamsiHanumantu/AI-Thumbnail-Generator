import asyncio
import logging
import traceback

from sqlmodel import Session, select

from database import engine
from models import Job, Thumbnail
from services.huggingface_service import generate_thumbnail
from services.imagekit_service import upload_file


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


STYLES = {
    "bold_dramatic": """
    Create a bold, dramatic YouTube thumbnail.

    STYLE:
    - High contrast
    - Cinematic lighting
    - Dark moody background
    - Powerful composition
    - Viral YouTube aesthetic

    SUBJECT:
    - Person's face should be large and prominent
    - Dramatic emotional expression
    - Strong eye contact
    - Sharp facial details

    EFFECTS:
    - Glow effects
    - Dynamic shadows
    - Cinematic depth
    """,

    "clean_minimal": """
    Create a clean, minimal YouTube thumbnail.

    STYLE:
    - Bright lighting
    - White/light background
    - Professional modern aesthetic
    - Minimal clutter
    - Sharp clean composition

    SUBJECT:
    - Person should look approachable
    - Professional appearance
    - Soft natural expression

    EFFECTS:
    - Smooth gradients
    - Soft shadows
    - Elegant spacing
    """,

    "vibrant_energetic": """
    Create a vibrant, energetic YouTube thumbnail.

    STYLE:
    - Colorful gradients
    - Dynamic composition
    - Eye-catching pop-art style
    - Modern creator aesthetic
    - Highly clickable design

    SUBJECT:
    - Excited engaging expression
    - Energetic pose
    - Bright lighting

    EFFECTS:
    - Neon glow
    - Motion energy
    - Dynamic background elements
    """,
}


STYLE_ORDER = [
    "bold_dramatic",
    "clean_minimal",
    "vibrant_energetic",
]


async def generate_single_thumbnail(
    thumbnail_id: str,
    prompt: str,
    headshot_url: str,
):

    # mark thumbnail generating
    with Session(engine) as session:
        thumbnail = session.get(Thumbnail, thumbnail_id)

        if not thumbnail:
            return

        thumbnail.status = "generating"

        style_name = thumbnail.style_name

        session.add(thumbnail)
        session.commit()

    style_prompt = STYLES[style_name]

    try:
        # AI generation
        image_bytes = await generate_thumbnail(
            prompt,
            style_prompt,
            headshot_url,
        )

        # get job id
        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)

            if not thumbnail:
                return

            job_id = thumbnail.job_id

        # upload image
        url = upload_file(
            filebytes=image_bytes,
            filename=f"{thumbnail_id}.png",
            folder=f"thumbnails/{job_id}",
        )

        # save uploaded result
        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)

            if not thumbnail:
                return

            thumbnail.imagekit_url = url
            thumbnail.status = "uploaded"

            session.add(thumbnail)
            session.commit()

        logger.info(
            f"Thumbnail {thumbnail_id} generated successfully"
        )

    except Exception as e:
        logger.error(
            f"Error generating thumbnail {thumbnail_id}: {str(e)}"
        )

        traceback.print_exc()

        with Session(engine) as session:
            thumbnail = session.get(Thumbnail, thumbnail_id)

            if not thumbnail:
                return

            thumbnail.status = "failed"
            thumbnail.error_message = str(e)[:500]

            session.add(thumbnail)
            session.commit()


async def populate_job(job_id: str):

    # mark job processing
    with Session(engine) as session:
        job = session.get(Job, job_id)

        if not job:
            return

        job.status = "processing"

        prompt = job.prompt
        headshot_url = job.headshot_url

        session.add(job)
        session.commit()

    # fetch thumbnails
    with Session(engine) as session:
        thumbnails = session.exec(
            select(Thumbnail).where(
                Thumbnail.job_id == job_id
            )
        ).all()

        thumbnail_ids = [
            thumbnail.id
            for thumbnail in thumbnails
        ]

    # parallel generation
    tasks = [
        generate_single_thumbnail(
            thumbnail_id,
            prompt,
            headshot_url,
        )
        for thumbnail_id in thumbnail_ids
    ]

    await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    # final job status update
    with Session(engine) as session:
        job = session.get(Job, job_id)

        if not job:
            return

        thumbnails = session.exec(
            select(Thumbnail).where(
                Thumbnail.job_id == job_id
            )
        ).all()

        all_failed = all(
            thumbnail.status == "failed"
            for thumbnail in thumbnails
        )

        if all_failed:
            job.status = "failed"
        else:
            job.status = "completed"

        session.add(job)
        session.commit()

    logger.info(f"Job {job_id} completed")