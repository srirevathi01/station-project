from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {
        "message": "Hello from FastAPI Root"
    }

@app.get("/fastapi")
@app.get("/fastapi/")
def home():
    return {
        "message": "Hello FastAPI"
    }
