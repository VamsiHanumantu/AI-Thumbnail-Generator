import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from routes import router
from database import create_tables
from fastapi.middleware.cors import CORSMiddleware

     

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(
    lifespan=lifespan,
    title="Youtube thumbnail generator"
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)