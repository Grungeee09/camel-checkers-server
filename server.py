from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict

app = FastAPI()


class RequestData(BaseModel):
    message: str
    metadata: Dict[str, str]


class ResponseData(BaseModel):
    response: str
    status: str


@app.post("/process")
async def process_data(data: RequestData) -> ResponseData:
    print(f"Получено сообщение: {data.message}")
    print(f"Метаданные: {data.metadata}")
    response_message = f"Сообщение '{data.message}' обработано!"
    return ResponseData(response=response_message, status="success")
