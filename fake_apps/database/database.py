import psycopg2

# params for database connection
GENERIC_DB_NAME = "postgres"
DB_NAME = "cities"
DB_USER = "postgres"
DB_PASSWORD = "newpassword"
PORT = "5432"
HOST_IP = "localhost"

TABLE_VALUES = [('Trento', 'Italy'), ('Helsinki', 'Finland'), ('Riga', 'Latvia'), ('Milan', 'Italy'), ('Kuopio', 'Finland')]

# function to establish db connection
def establish_connection(db_name):
    try:
        connection = psycopg2.connect(
            dbname = db_name,
            user = DB_USER,
            password = DB_PASSWORD,
            host = HOST_IP,
            port = PORT
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

# function to establish db connection
def connect_db():
    try:
        connection = ''
        cursor = ''

        # establish generic db connection
        connection_first, cursor_first = establish_connection(GENERIC_DB_NAME)

        # check if mock db exists
        cursor_first.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")
        exists = cursor_first.fetchone()

        if not exists:
            connection, cursor = create_db(connection_first, cursor_first)
        else:
            connection, cursor = establish_connection(DB_NAME)
        close_connection(connection_first, cursor_first)
        return connection, cursor

    except Exception as e:
        print(f"An error occurred: {e}")

# function to create postgres database and table
def create_db(connection_generic, cursor_generic):
    try:
        print("Database container is being created.")

        # create mock db
        cursor_generic.execute(f"CREATE DATABASE {DB_NAME};")
        connection_generic.commit()

        # close generic connection
        close_connection(connection_generic, cursor_generic)

        # establish connection to new db
        connection, cursor = establish_connection(DB_NAME)
        
        # create table in db
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_cities_data 
                (id SERIAL PRIMARY KEY, 
                city VARCHAR(50), 
                country VARCHAR(50));
        """)
        connection.commit()

        add_mock_data(connection, cursor)

        print(f"Database {DB_NAME} created.")
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
        return

# main function
if __name__ == "__main__":

    # establish db connection
    connection, cursor = connect_db()

    while True:
        # verify db table correctness
        print_mock_table(cursor)
        #print("ciao",flush=True)
        #time.sleep(3)

    close_connection(connection, cursor)
