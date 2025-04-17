import os
import random
import string
import smtplib
import time
import mysql.connector
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Literal


class MessageResponse(BaseModel):
    message: str


class JoinGameResponse(BaseModel):
    game_id: int | None
    side: Literal["w", "b"] | None


class LoginData(BaseModel):
    nickname: str
    password: str


class AccountData(LoginData):
    email: str


class AccountConfirmationData(AccountData):
    code: str
    time: int


class StartRegistrationResponse(BaseModel):
    id: int


class FinishRegistrationRequest(StartRegistrationResponse):
    code: str


def check_in_game(user_data: tuple) -> bool:
    for players in server_games.keys():
        if user_data in players:
            return True
    return False


def delete_expired_codes() -> None:
    all_codes: tuple = tuple(server_codes.items())
    for id_, other in all_codes:
        if other.time < time.time() - 600 and id_ in server_codes:
            del server_codes[id_]


def delete_expired_queue() -> None:
    all_queue: tuple = tuple(server_queue.items())
    for login_data, last_time in all_queue:
        if time.time() - last_time > 15:
            del server_queue[login_data]


def create_game(user1_data: tuple[str, str], user2_data: tuple[str, str]) -> dict:
    game_id: int = max(server_games.keys()) + 1 if len(server_games) > 0 else 0

    random_int: int = random.randint(0, 1)
    sides: dict = {user1_data: "w" if random_int == 0 else "b",
                   user2_data: "w" if random_int == 1 else "b"}

    board: dict = {}

    for x in range(8):
        for y in range(8):
            if (x + y) % 2 == 1:
                if x < 3:
                    board[(x, y)] = 'wd'  # {w - white, b - black}{d - default, q - queen}
                elif x > 4:
                    board[(x, y)] = 'bd'
                else:
                    board[(x, y)] = ''
            else:
                board[(x, y)] = ''

    server_games[(user1_data, user2_data)] = {"sides": sides, "board": board, "id": game_id}

    return server_games[(user1_data, user2_data)]


server_codes: dict[int, AccountConfirmationData] = {}
server_queue: dict[tuple, float] = {}
server_games: dict[tuple, dict] = {}


load_dotenv("etc/secrets/.env")

app = FastAPI()
sql = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_USER"),
    port=os.getenv("MYSQL_PORT"),
    connection_timeout=10
)

cursor = sql.cursor(buffered=True)

cursor.execute("CREATE TABLE IF NOT EXISTS users("
               "nickname VARCHAR(50) PRIMARY KEY,"
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
            id_ = max(server_codes.keys()) + 1 if server_codes else 0

            server_codes[id_] = AccountConfirmationData(nickname=data.nickname, password=data.password,
                                                        email=data.email, code=code, time=int(time.time()))
            return StartRegistrationResponse(id=id_)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error sending email: {e}")


@app.post("/finish_registration")
async def finish_registration(data: FinishRegistrationRequest) -> MessageResponse:
    if data.id in server_codes and server_codes[data.id].code == data.code:
        insert_query = "INSERT INTO users (nickname, password, email, queue, in_game) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (server_codes[data.id].nickname, server_codes[data.id].password,
                                      server_codes[data.id].email))
        sql.commit()

        del server_codes[data.id]

        return MessageResponse(message="Account created successfully")
    else:
        raise HTTPException(status_code=400, detail="Incorrect code")


@app.post("/login")
async def login(data: LoginData) -> MessageResponse:
    cursor.execute("SELECT password FROM users WHERE nickname = %s", (data.nickname,))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=400, detail="User with that nickname does not exist")
    elif result[0] == data.password:
        return MessageResponse(message="Login successful")
    else:
        raise HTTPException(status_code=400, detail="Incorrect password")


@app.post("/join_queue")
async def join_queue(data: LoginData) -> MessageResponse:
    delete_expired_queue()

    cursor.execute("SELECT nickname, password FROM users WHERE nickname = %s", (data.nickname,))
    row: tuple | None = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=400, detail="Invalid user data (user does not exist)")

    nickname, password = row

    if (data.nickname, data.password) in server_queue:
        raise HTTPException(status_code=409, detail="User with this nickname is already in queue")
    elif nickname != data.nickname or password != data.password:
        raise HTTPException(status_code=400, detail="Invalid user data")
    else:
        server_queue[(nickname, password)] = time.time()

        return MessageResponse(message="Success")


@app.post("/update_queue")
async def update_queue(data: LoginData) -> JoinGameResponse:
    delete_expired_queue()
    user_data = (data.nickname, data.password)

    if game_players := check_in_game(user_data):
        if user_data in server_queue:
            game_data: dict = server_games[game_players]

            del server_queue[user_data]

            return JoinGameResponse(game_id=game_data["id"], side=game_data["sides"][user_data])
        else:
            raise HTTPException(status_code=400, detail="User already in game")

    if user_data in server_queue.keys():
        server_queue[user_data] = time.time()

        if len(server_queue) > 1:
            for other_data in server_queue:
                if other_data != user_data:
                    game_data: tuple = create_game(user_data, other_data)

                    side: Literal["w", "b"] = game_data["sides"][user_data]
                    game_id: int = game_data["id"]

                    del server_queue[user_data]

                    return JoinGameResponse(game_id=game_id, side=side)

        return JoinGameResponse(game_id=None, side=None)
    else:
        raise HTTPException(status_code=400, detail="User not in queue")


@app.post("/leave_queue")
async def leave_queue(data: LoginData) -> MessageResponse:
    login_data = (data.nickname, data.password)

    if login_data in server_queue:
        del server_queue[login_data]

        return MessageResponse(message="Success")
    else:
        raise HTTPException(status_code=400, detail="User not in queue")
