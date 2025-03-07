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
            dbname = DB_NAME,
            user = DB_USER,
            password = DB_PASSWORD,
            host = HOST_IP,
            port = PORT
        )
        connection.autocommit = True
        cursor = connection.cursor()
    except Exception as e:
        connection = psycopg2.connect(
            dbname = 'postgres',
            user = DB_USER,
            password = DB_PASSWORD,
            host = HOST_IP,
            port = PORT
        )
        create_db(connection, cursor)
        connection.autocommit = True
        cursor = connection.cursor()
    finally:
        return connection, cursor

# function to create postgresql database and table
def create_db(connection, cursor):
    try:
        print("Database container is being created.")

        # check if the database already exists
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"CREATE DATABASE {DB_NAME}.")
            print(f"Database {DB_NAME} created.")

            # create table in db
            cursor.execute(f"CREATE TABLE IF NOT EXISTS mock_cities_data (id SERIAL PRIMARY KEY, city VARCHAR(50), country VARCHAR(50));")
            connection.commit()
        else:
            print(f"Database '{DB_NAME}' already exists. No action taken.")

    except Exception as e:
        print(f"An error occurred: {e}")

# function to add mock data into database
def add_mock_data(connection, cursor):
    try:
        # insert values in db table
        cursor.executemany("INSERT INTO mock_cities_data (city, country) VALUES (%s, %s);", TABLE_VALUES)
        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")

# function to verify correctness of table
def print_mock_table(connection, cursor):
    try:
        query = "SELECT * FROM mock_cities_data;"
        args = ','.join(cursor.mogrify("(%s, %s)", row).decode() for row in TABLE_VALUES)
        
        cursor.execute(query % args)
        connection.commit()

    except Exception as e:
        print(f"An error occurred: {e}")
        return

# main function
if __name__ == "__main__":
    
    # establis connection
    connection, cursor = establish_connection()
    
    # create database if not yet existing
    database = create_db(cursor)
    
    
    if database:
        add_mock_data(database)
        print_mock_table(database)
    
    # close connection
    cursor.close() 
    connection.close()
