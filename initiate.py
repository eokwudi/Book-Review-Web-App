import os
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

def main():
    user = "abc"
    passw = "123"
    db.execute("INSERT INTO people (username, password) VALUES (:username, :password)",
    {"username": user, "password": passw})
    print("hello")
    db.commit()

if __name__ == "__main__":
    main()
