from fastapi import FastAPI

from agent_memory_project.api.langmem_api import LangmemAPI
from agent_memory_project.api.lifespan import lifespan_manager
from agent_memory_project.api.memory_api import MemoryAPI
from agent_memory_project.api.schemas import CommonRes
from agent_memory_project.core.config import SETTINGS

app = FastAPI(
    title=SETTINGS.api_title,
    description=SETTINGS.api_description,
    version=SETTINGS.api_version,
    lifespan=lifespan_manager,
)


@app.get("/health")
async def health() -> CommonRes[dict[str, str]]:
    return CommonRes.success({"status": "ok"})


memory_api = MemoryAPI()
app.include_router(memory_api.router)

langmem_api = LangmemAPI()
app.include_router(langmem_api.router)
