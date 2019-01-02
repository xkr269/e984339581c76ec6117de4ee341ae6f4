#! /usr/bin/python3

import maprdb

# MaprDB
def open_db():
    return (maprdb.connect())

def open_table(connection, table_path):
    if connection.exists(table_path):
        return (connection.get(table_path))
    return (connection.create(table_path))