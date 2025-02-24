import os
import random
import string
import smtplib
import time
import mysql.connector
from hashlib import sha256
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv


class MessageResponse(BaseModel):
    message: str


class AccountData(BaseModel):
    nickname: str
    password: str
    email: str


class AccountConfirmationData(AccountData):
    code: str
    time: int


class StartRegistrationResponse(MessageResponse):
    id: int


class FinishRegistrationRequest(BaseModel):
    id: int
    code: str


def delete_expired_codes():
    try:
        all_codes: list = list(codes.items())
        for id_, other in all_codes:
            if other["time"] < time.time() - 600 and id_ in codes:
                del codes[id_]
    except Exception as e:
        print(e)


def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()


codes: dict[int, AccountConfirmationData] = {}

load_dotenv("etc/secrets/.env")

app = FastAPI()
sql = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_USER"),
    port=os.getenv("MYSQL_PORT")
)

cursor = sql.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users("
               "id INT PRIMARY KEY AUTO_INCREMENT,"
               "nickname VARCHAR(50) NOT NULL,"
               "password VARCHAR(255) NOT NULL,"
               "email VARCHAR(255) NOT NULL)")
sql.commit()


@app.post("/start_registration")
async def start_registration(data: AccountData) -> StartRegistrationResponse:
    cursor.execute("SELECT COUNT(*) FROM users WHERE nickname = %s", (data.nickname,))
    if cursor.fetchone()[0] > 0:
        raise HTTPException(status_code=400, detail="Nickname already exists")

    cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s", (data.email,))
    if cursor.fetchone()[0] >= 3:
        raise HTTPException(status_code=400, detail="One email cannot be used more than 3 times")

    delete_expired_codes()
    code = ''.join(random.choices(string.digits, k=6))

    sender_email: str = os.getenv("EMAIL")
    sender_password: str = os.getenv("EMAIL_PASSWORD")
    message: str = (f"Subject: Confirmation Code\n\nYour confirmation code: {code}\n\n"
                    f"If you haven't triggered any checks, just ignore this message.")

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:  # Для Gmail
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, data.email, message)
            id_ = max(codes.keys())+1 if codes else 0

            codes[id_] = AccountConfirmationData(nickname=data.nickname, password=hash_password(data.password),
                                                 email=data.email, code=code, time=int(time.time()))
            return StartRegistrationResponse(message="Email sent successfully!", id=id_)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error sending email: {e}")


@app.post("/finish_registration")
def finish_registration(data: FinishRegistrationRequest) -> MessageResponse:
    if data.id in codes and codes[data.id].code == data.code:
        insert_query = "INSERT INTO users (nickname, password, email) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (codes[data.id].nickname, codes[data.id].password, codes[data.id].email))
        sql.commit()
        return MessageResponse(message="Account created successfully")
    else:
        raise HTTPException(status_code=400, detail="Incorrect code")
