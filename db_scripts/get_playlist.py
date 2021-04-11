import pymysql
import configparser

config = configparser.ConfigParser()
config.read('../config.ini')
database_config = dict(config.items('Database'))

conn = pymysql.connect(database_config['host'],
                       database_config['userid'],
                       database_config['password'],
                       database_config['databasename'])

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
