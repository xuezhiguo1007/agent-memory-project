import uvicorn


if __name__ == "__main__":
    uvicorn.run(
        "agent_memory_project.api.main:app",
        host="localhost",
        port=8000,
        reload=True,
    )
