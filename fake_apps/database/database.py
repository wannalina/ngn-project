import psycopg2

# params for database connection
DB_NAME = "cities"
DB_USER = "postgres"
DB_PASSWORD = "newpassword"
PORT = "5432"
HOST_IP = "localhost"

TABLE_VALUES = [('Trento', 'Italy'), ('Helsinki', 'Finland'), ('Riga', 'Latvia'), ('Milan', 'Italy'), ('Kuopio', 'Finland')]

# function to establish db connection
def establish_connection():
    try:
        connection = psycopg2.connect(
            dbname = 'postgres',
            user = DB_USER,
            password = DB_PASSWORD,
            host = HOST_IP,
            port = PORT
        )
        connection.autocommit = True
        cursor = connection.cursor()
    
        # check if the database already exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")
        exists = cursor.fetchone()

        if not exists:
            create_db(connection, cursor)
        else:
            connection = psycopg2.connect(
                dbname = DB_NAME,
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

# function to create postgresql database and table
def create_db(connection, cursor):
    try:
        print("Database container is being created.")

        cursor.execute(f"CREATE DATABASE {DB_NAME};")

        # create table in db
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mock_cities_data 
                (id SERIAL PRIMARY KEY, 
                city VARCHAR(50), 
                country VARCHAR(50));
        """)
        connection.commit()
        print("????????")
        add_mock_data(connection, cursor)

        print(f"Database {DB_NAME} created.")

    except Exception as e:
        print(f"An error occurred: {e}")

# function to add mock data into database
def add_mock_data(connection, cursor):
    try:
        print("working 1")
        # insert values in db table
        cursor.executemany("INSERT INTO mock_cities_data (city, country) VALUES (%s, %s);", TABLE_VALUES)
        connection.commit()
        
        print("working 2")

    except Exception as e:
        print(f"An error occurred: {e}")

# function to verify correctness of table
def print_mock_table(connection, cursor):
    try:
        print("here??")
        query = "SELECT * FROM mock_cities_data;"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for row in rows:
            print(row)
        print("yeah no")

    except Exception as e:
        print(f"An error occurred: {e}")
        return

# main function
if __name__ == "__main__":

    # establish connection
    connection, cursor = establish_connection()

 #   add_mock_data(connection, cursor)
    print_mock_table(connection, cursor)

    # close connection
    cursor.close() 
    connection.close()
