from fastapi import FastAPI

from app.tasks import router as task_router

app = FastAPI(title="factory-sample-app")


@app.get("/hello")
def hello():
    return {"message": "Hello, World!"}


app.include_router(task_router)
