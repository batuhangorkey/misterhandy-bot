import pymysql
from bot_data import bot_data

HOST = bot_data["HOST"]
USER_ID = bot_data["USER_ID"]
PASSWORD = bot_data["PASSWORD"]
DATABASE_NAME = bot_data["DATABASE_NAME"]

conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)

try:
    with conn.cursor() as cursor:
        cursor.execute("UPDATE")
    conn.commit()
finally:
    conn.close()
