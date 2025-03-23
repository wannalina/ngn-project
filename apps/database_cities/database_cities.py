import psycopg2
import os
import signal

TABLE_VALUES = [('Trento', 'Italy'), ('Helsinki', 'Finland'), ('Bolzano', 'Italy'), ('Washington DC', 'USA'), ('Barcelona', 'Spain')]

# function to establish db connection
def establish_connection(db_name):
    try:
        connection = psycopg2.connect(
            dbname = db_name,
            user = os.getenv('DB_USER'),
            password = os.getenv('DB_PASSWORD'),
            host = os.getenv('HOST_IP'),
            port = os.getenv('PORT')
        )
        connection.autocommit = True
        cursor = connection.cursor()
        return connection, cursor
    except Exception as e: 
        print(f"An error occurred: {e}")

# function to close db connection
def close_connection(connection, cursor):
    connection.close()
    cursor.close()
    
def handle_sigterm(signum, frame, connection, cursor):
    close_connection(connection, cursor)

# function to create db
def connect_db():
    try:
        connection = None
        cursor = None

        # establish generic db connection
        connection_first, cursor_first = establish_connection(os.getenv('GENERIC_DB_NAME'))

        # check if mock db exists
        cursor_first.execute(f"SELECT 1 FROM pg_database WHERE datname = '{os.getenv('DB_NAME')}';")
        exists = cursor_first.fetchone()

        if not exists:
            connection, cursor = create_db(connection_first, cursor_first)
        else:
            connection, cursor = establish_connection(os.getenv('DB_NAME'))
        close_connection(connection_first, cursor_first)
        return connection, cursor

    except Exception as e:
        print(f"An error occurred: {e}")

# function to create postgres database and table
def create_db(connection_generic, cursor_generic):
    try:
        print("Database container is being created.")

        # create mock db
        cursor_generic.execute(f"CREATE DATABASE {os.getenv('DB_NAME')};")
        connection_generic.commit()

        # close generic connection
        close_connection(connection_generic, cursor_generic)

        # establish connection to new db
        connection, cursor = establish_connection(os.getenv('DB_NAME'))
        
        # create table in db
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_cities_data 
                (id SERIAL PRIMARY KEY, 
                city VARCHAR(50), 
                country VARCHAR(50)), 
                temperature(INT(60));
        """)
        connection.commit()

        add_mock_data(connection, cursor)

        print(f"Database {os.getenv('DB_NAME')} created.")
        return connection, cursor

    except Exception as e:
        print(f"An error occurred: {e}")

# function to add mock data into database
def add_mock_data(connection, cursor):
    try:
        # insert values in table
        cursor.executemany("INSERT INTO mock_cities_data (city, country) VALUES (%s, %s);", TABLE_VALUES)
        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")

# function to fetch db table rows
def print_mock_table(cursor):
    try:
        query = "SELECT * FROM mock_cities_data;"
        cursor.execute(query)
        rows = cursor.fetchall()     

        # print each table row
        for row in rows:
            print(row, flush=True)

    except Exception as e:
        print(f"An error occurred: {e}")

# main function
if __name__ == "__main__":
    # establish db connection
    connection, cursor = connect_db()
    
    # register sigterm handler for connection shutdown if container terminated
    signal.signal(signal.SIGTERM, lambda signum, frame: handle_sigterm(signum, frame, connection, cursor))

    # verify db correctness
    print_mock_table(cursor)

    try:        
        # keep db connection open until container terminated
        while True: 
            pass
    except Exception as e:
        close_connection(connection, cursor)
    
#docker build -t random_logger .
#docker save random_logger -o random_logger.tar
#docker load -i random_logger.tar
