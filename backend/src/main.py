from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from random import random

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World" if random() <= 0.5 else "Greetings World"}
