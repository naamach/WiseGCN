import pymysql.cursors
from configparser import ConfigParser
import logging

config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')

conn = pymysql.connect(host=config.get('DB', 'HOST'),
                       user=config.get('DB', 'USER'),
                       passwd=config.get('DB', 'PASSWD'),
                       db=config.get('DB', 'DB'),
                       unix_socket=config.get('DB', 'SOCKET'))


def insert_values(table, dict_to_insert):
    keys = dict_to_insert.keys()
    vals = [str(dict_to_insert[key]) for key in keys]
    query = 'INSERT INTO {} (`{}`) VALUES ({});'.format(table, '`, `'.join(keys), ', '.join('{}'.format('"{}"'.format(v) if "SELECT" not in v else v) for v in vals))
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    try:
        cursor.execute(query)
    except pymysql.err.InternalError as e:
        code, msg = e.args
        logging.error("Failed to insert values into table {}.".format(table))
        logging.error("Error code = {}".format(code))
        logging.error(msg)
    conn.commit()
    cursor.close()


def get_columns(table):
    query = "SELECT `COLUMN_NAME` FROM `INFORMATION_SCHEMA`.`COLUMNS` WHERE `TABLE_NAME`='{}';".format(table)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    cursor.execute(query)
    col = cursor.fetchall()
    cursor.close()
    cols = [x['COLUMN_NAME'] for x in col if 'COLUMN_NAME' in x]
    return cols


def insert_voevent(table, params):
    # Remove keys not included in the table
    cols = get_columns(table)
    dict_to_insert = dict(params)
    for key in params.keys():
        if key not in cols:
            dict_to_insert.pop(key, None)
    # Insert values to table
    insert_values(table, dict_to_insert)
