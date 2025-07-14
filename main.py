from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

app = FastAPI(title="FastAPI Demo")

@app.get("/")
async def root():
    return {"msg": "FastAPI is running 🎉"}