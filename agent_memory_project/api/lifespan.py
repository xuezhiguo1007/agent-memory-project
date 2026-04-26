from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan_manager(app: FastAPI):
    yield
