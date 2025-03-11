import psycopg2
import os
import signal

# example bookstore data
BOOKS_DATA = [
    ('The Great Gatsby', 'F. Scott Fitzgerald', 1925),
    ('To Kill a Mockingbird', 'Harper Lee', 1960),
    ('1984', 'George Orwell', 1949),
    ('Moby Dick', 'Herman Melville', 1851),
    ('War and Peace', 'Leo Tolstoy', 1869)
]

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

# Function to handle container shutdown (SIGTERM)
def handle_sigterm(signum, frame, connection, cursor):
    close_connection(connection, cursor)

# function to connect to the database
def connect_db():
    try:
        connection = None
        cursor = None

        # establish connection to the generic db
        connection_first, cursor_first = establish_connection(os.getenv('GENERIC_DB_NAME'))

        # check if bookstore database exists
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

# function to create the postgres database and table
def create_db(connection_generic, cursor_generic):
    try:
        print("Creating database for the bookstore...")

        # create the bookstore database
        cursor_generic.execute(f"CREATE DATABASE {os.getenv('DB_NAME')};")
        connection_generic.commit()

        # close the generic connection
        close_connection(connection_generic, cursor_generic)

        # establish a connection to the new database
        connection, cursor = establish_connection(os.getenv('DB_NAME'))
        
        # create the books table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255),
                author VARCHAR(255),
                publication_year INT
            );
        """)
        connection.commit()

        # add mock data
        add_mock_data(connection, cursor)

        print(f"Database {os.getenv('DB_NAME')} created successfully.")
        return connection, cursor

    except Exception as e:
        print(f"An error occurred: {e}")

# function to add mock data into the books table
def add_mock_data(connection, cursor):
    try:
        cursor.executemany("INSERT INTO books (title, author, publication_year) VALUES (%s, %s, %s);", BOOKS_DATA)
        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")

# function to fetch the books table rows
def print_books_table(cursor):
    try:
        query = "SELECT * FROM books;"
        cursor.execute(query)
        rows = cursor.fetchall()

        # print each row from the table
        for row in rows:
            print(row, flush=True)

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # establish connection to the bookstore database
    connection, cursor = connect_db()

    # register sigterm handler to cleanly shutdown the connection if the container is terminated
    signal.signal(signal.SIGTERM, lambda signum, frame: handle_sigterm(signum, frame, connection, cursor))

    # print the books from the database to verify
    print_books_table(cursor)

    try:
        # keep the connection open until the container is terminated
        while True:
            pass
    except Exception as e:
        close_connection(connection, cursor)
