import psycopg2
import os
import signal
import time

TABLE_VALUES = [
    ('Trento', 'Italy'),
    ('Helsinki', 'Finland'),
    ('Bolzano', 'Italy'),
    ('Washington DC', 'USA'),
    ('Barcelona', 'Spain')
]

def establish_connection(db_name):
    return psycopg2.connect(
        dbname=db_name,
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('HOST_IP', 'localhost'),
        port=os.getenv('PORT', '5432')
    )

def close_connection(connection, cursor):
    cursor.close()
    connection.close()

def handle_sigterm(signum, frame):
    print("SIGTERM received, exiting")
    exit(0)

def connect_db():
    connection_first, cursor_first = establish_connection(os.getenv('GENERIC_DB_NAME')),
    cursor_first = connection_first.cursor()
    cursor_first.execute(f"SELECT 1 FROM pg_database WHERE datname = '{os.getenv('DB_NAME')}';")
    exists = cursor_first.fetchone()

    if not exists:
        create_db(connection_first, cursor_first)
    else:
        connection, cursor = establish_connection(os.getenv('DB_NAME')),
        cursor = connection.cursor()
        print("Mock database already exists.")
        return connection, cursor

def create_db(connection_generic, cursor_generic):
    cursor_generic.execute(f"CREATE DATABASE {os.getenv('DB_NAME')};")
    connection_generic.commit()
    close_connection(connection_generic, cursor_generic)
    connection, cursor = establish_connection(os.getenv('DB_NAME')),
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mock_cities_data (
            id SERIAL PRIMARY KEY,
            city VARCHAR(50),
            country VARCHAR(50)
        );
    """)
    connection.commit()
    add_mock_data(connection, cursor)
    print(f"Database {os.getenv('DB_NAME')} initialized.")
    return connection, cursor

def add_mock_data(connection, cursor):
    cursor.executemany("INSERT INTO mock_cities_data (city, country) VALUES (%s, %s);", TABLE_VALUES)
    connection.commit()

def print_mock_table(cursor):
    cursor.execute("SELECT * FROM mock_cities_data;")
    for row in cursor.fetchall():
        print(row)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_sigterm)
    connection, cursor = connect_db()
    print_mock_table(cursor)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        close_connection(connection, cursor)