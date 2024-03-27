import datetime

import databases
import sqlalchemy

import hashlib

import uvicorn
from fastapi import FastAPI, HTTPException

from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr, SecretStr
from sqlalchemy import create_engine

DATABASE_URL = 'sqlite:///database.db'
database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

app = FastAPI()

users = sqlalchemy.Table("users", metadata,
                         sqlalchemy.Column("user_id", sqlalchemy.Integer, autoincrement=True, primary_key=True),
                         sqlalchemy.Column('username', sqlalchemy.String(length=30)),
                         sqlalchemy.Column('email', sqlalchemy.String(length=100)),
                         sqlalchemy.Column('password', sqlalchemy.String(length=300)),
                         sqlalchemy.Column('first_name', sqlalchemy.String(length=300)),
                         sqlalchemy.Column('last_name', sqlalchemy.String(length=300)),
                         sqlalchemy.Column('address', sqlalchemy.String(length=300)),
                         sqlalchemy.Column('birth_date', sqlalchemy.Date()))

metadata.create_all(engine)


class User(BaseModel):
    username: str = Field(title="Username", max_length=30)
    email: EmailStr = Field(title="Email", max_length=100)
    first_name: str = Field(title="First Name", max_length=100, min_length=2, default=None)
    last_name: str = Field(title="Last Name", max_length=100, min_length=2, default=None)
    password: SecretStr = Field(title="Password")
    address: str = Field(title="Address", min_length=5, default=None)
    birth_date: datetime.date = Field(title="Birth Date", default=None)


class UserWithId(User):
    user_id: int = Field(title="id", description="ID of user")


@app.get("/create_fake_users")
async def user_list_generator():
    result = []
    for i in range(4):
        username = "user_" + str(i)
        email = str(username) + '@mail.mail'
        password = 'pass_' + str(i)
        first_name = 'first_name_' + str(i)
        last_name = 'last_name_' + str(i)
        address = 'address_' + str(i)
        birth_date = datetime.date(1999 - i, 12 - i, i + 1)
        data = {"username": username, "email": email, "password": password, "first_name": first_name,
                "last_name": last_name, "address": address, "birth_date": birth_date}
        user = User(**data)
        await database.execute(users.insert().values(**data))
    return "OK"


@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event('shutdown')
async def shutdown():
    await database.disconnect()


@app.get("/")
async def root():
    return {"message": "root"}


@app.get("/users", response_model=List[UserWithId])
async def get_users():
    query = users.select()
    return await database.fetch_all(query)


@app.get("/users/{user_id}", response_model=UserWithId)
async def get_user_by_id(user_id: int):
    fetched_data = await database.fetch_one(users.select().where(users.c.user_id == user_id))
    if not fetched_data:
        raise HTTPException(status_code=404, detail="User not found")
    return fetched_data


@app.post("/new_user")
async def create_user(user: User, response_model=UserWithId):
    result = user.model_dump()
    user.password = user.password.get_secret_value()
    query = users.insert().values(**user.model_dump())
    print(f'{user.model_dump()}')
    last_user_id = await database.execute(query)
    return {**result, 'user_id': last_user_id}


@app.put("/users/{user_id}", response_model=UserWithId)
async def update_user(user_id: int, user: User):
    if not await database.fetch_one(users.select().where(users.c.user_id == user_id)):
        raise HTTPException(status_code=404, detail="User not found")
    result = user.model_dump()
    user.password = user.password.get_secret_value()
    query = users.update().where(users.c.user_id == user_id).values(**user.model_dump())
    await database.execute(query)
    return {**result, 'user_id': user_id}


@app.delete("/users/{user_id}")
async def delete_user(user_id: int):
    if not await database.fetch_one(users.select().where(users.c.user_id == user_id)):
        raise HTTPException(status_code=404, detail="User not found")
    query = users.delete().where(users.c.user_id == user_id)
    return {'OK'}


if __name__ == '__main__':
    uvicorn.run("main_user:app", host='127.0.0.1', port=80, reload=True)
