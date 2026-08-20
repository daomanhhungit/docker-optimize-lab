from fastapi import FastAPI
from pydantic import BaseModel
import time
import platform

app = FastAPI(title="Docker Optimize Lab", version="0.1.0")


class Item(BaseModel):
    name: str
    price: float


@app.get("/")
def root():
    return {"message": "Hello from docker-optimize-lab"}


@app.get("/health")
def health():
    return {"status": "ok", "python": platform.python_version(), "ts": time.time()}


@app.post("/items")
def create_item(item: Item):
    return {"received": item.model_dump(), "total_with_tax": round(item.price * 1.1, 2)}
