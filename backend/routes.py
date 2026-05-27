from fastapi import APIRouter, HTTPException,Depends,UploadFile,File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session,select
import logging
import os
import json

from database import get_session
from models import Job,Thumbnail
from services.generator import populate_job, STYLE_ORDER
from services.imagekit_service import get_variants,upload_file
import asyncio



logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

# request and response schema

class CreateJobRequest(BaseModel):
    prompt: str
    headshot_url: str
    num_thumbnails: int

class CreateJobResponse(BaseModel):
    job_id: str

class ThumbnailResponse(BaseModel):
    id: str
    style_name: str
    status: str
    imagekit_url: str | None = None
    error_message: str | None = None
    variants: dict | None = None

class JobResponse(BaseModel):
    id: str
    prompt: str
    num_thumbnails: int
    headshot_url: str
    status: str
    thumbnails: list[ThumbnailResponse]

@router.post("/upload-headshot")
async def upload_headshot(file: UploadFile = File(...)):
    contents = await file.read()
    url = upload_file(
        filebytes=contents,
        filename=file.filename or "headshot.jpg",
        folder="headshots",
        content_type=file.content_type or "image/png",
    )

    return {"url": url}

@router.post("/jobs", response_model= CreateJobResponse)
async def create_job(request: CreateJobRequest, session: Session = Depends(get_session)):
    if request.num_thumbnails not in [1,2,3]:
        raise HTTPException(status_code=400, detail="Invalid number of thumbnails")
    
    job = Job(
        prompt=request.prompt,
        headshot_url=request.headshot_url,
        num_thumbnails=request.num_thumbnails,
    )
    session.add(job)

    styles = STYLE_ORDER[:request.num_thumbnails]

    for style_name in styles:
        thumbnail = Thumbnail(
            job_id=job.id,
            style_name=style_name,
        )
        session.add(thumbnail)
    
    session.commit()


    #fire and forgot style generation
    asyncio.create_task(populate_job(job.id))

    return CreateJobResponse(job_id=job.id)

@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    thumbnails = session.exec(
        select(Thumbnail).where(Thumbnail.job_id == job_id)
    ).all() 

    thumbnail_responses = []
    for thumbnail in thumbnails:
        variants = get_variants(thumbnail.imagekit_url)
        thumbnail_responses.append(
            ThumbnailResponse(
                id=thumbnail.id,
                style_name=thumbnail.style_name,
                status=thumbnail.status,
                imagekit_url=thumbnail.imagekit_url,
                error_message=thumbnail.error_message,
                variants=variants,  
                )
        )

    return JobResponse(
            id=job.id,
            prompt=job.prompt,
            headshot_url=job.headshot_url,
            num_thumbnails=job.num,   
            status=job.status,
            thumbnails=thumbnail_responses,
        )

@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: str):
    async def event_generator():
        from database import engine
        sent_thumbnails = set()

        while True:
            with Session(engine) as session:
                job = session.get(Job, job_id)
                if not job:
                    yield f"event: error\ndata: Job not found\n\n"
                    return
                thumbnails = session.exec(
                    select(Thumbnail).where(Thumbnail.job_id == job_id)
                ).all()

                for t in thumbnails:
                    if t.id in sent_thumbnails:
                        continue

                    if t.status == "uploaded":
                        sent_thumbnails.add(t.id)
                        variants = get_variants(t.imagekit_url)
                        data = json.dumps(
                            {
                                "id": t.id,
                                "style_name": t.style_name,
                                "status": t.status,
                                "imagekit_url": t.imagekit_url,
                                "variants": variants,
                            }
                        )   
                        yield f"event: thumbnail_ready\ndata: {data}\n\n"
                        sent_thumbnails.add(t.id)
                    elif t.status == "failed":
                        data = json.dumps(
                            {
                                "id": t.id,
                                "style_name": t.style_name,
                                "error_message": t.error_message,
                            }
                        )
                        yield f"event: thumbnail_failed\ndata: {data}\n\n"
                        sent_thumbnails.add(t.id)
                all_done = all(t.status in ("uploaded", "failed")for t in thumbnails)
                if all_done and len(sent_thumbnails) == len(thumbnails):
                    data = json.dumps(
                        {
                            "job_id": job_id,
                            "status": job.status
                        }
                    )
                    yield f"event: job_complete\ndata: {data}\n\n"
                    return
                await asyncio.sleep(1.5)
                    

    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        )