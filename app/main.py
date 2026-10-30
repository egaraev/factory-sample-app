from fastapi import FastAPI

app = FastAPI(title="factory-sample-app")


@app.get("/hello")
def hello():
    return {"message": "Hello, World!"}