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
        cursor.execute("UPDATE")
    conn.commit()
finally:
    conn.close()
