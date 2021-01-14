import pymysql
from bot_data import bot_data

HOST = bot_data["HOST"]
USER_ID = bot_data["USER_ID"]
PASSWORD = bot_data["PASSWORD"]
DATABASE_NAME = bot_data["DATABASE_NAME"]


conn = pymysql.connect(HOST, USER_ID, PASSWORD, DATABASE_NAME)

try:
    with conn.cursor() as cursor:
        cursor.execute("SELECT url, dislike, like_count FROM playlist")
        data = cursor.fetchall()
finally:
    conn.close()
if data:
    data = [t for t in data]
    data.sort(key=lambda e: int(e[2] / e[1]))
    [print(t, i, l) for t, i, l in data]
    print(len(data))
else:
    print('Empty data')
