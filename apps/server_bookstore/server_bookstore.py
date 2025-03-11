import psycopg2
from flask import Flask, request, jsonify
import os

# initialize Flask app
app = Flask(__name__)

# function to establish a connection to the database
def establish_connection(db_name):
    try:
        connection = psycopg2.connect(
            dbname = db_name,
            user = os.getenv('DB_USER'),
            password = os.getenv('DB_PASSWORD'),
            host = os.getenv('DB_HOST'),
            port = os.getenv('DB_PORT')
        )
        connection.autocommit = True
        cursor = connection.cursor()
        return connection, cursor
    except Exception as e:
        print(f"An error occurred: {e}")

# function to close the database connection
def close_connection(connection, cursor):
    connection.close()
    cursor.close()

# route to get all books from the database
@app.route('/books', methods=['GET'])
def get_books():
    try:
        connection, cursor = establish_connection(os.getenv('DB_NAME'))

        # query to fetch all books from the books table
        cursor.execute("SELECT * FROM books;")
        rows = cursor.fetchall()

        # format the result into a list of dictionaries
        books = [{"id": row[0], "title": row[1], "author": row[2], "publication_year": row[3]} for row in rows]

        close_connection(connection, cursor)

        return jsonify(books)

    except Exception as e:
        return f"An error occurred: {e}"

# route to insert a new book into the database
@app.route('/books', methods=['POST'])
def add_book():
    try:
        # get the book data from the request body (JSON)
        data = request.get_json()
        title = data['title']
        author = data['author']
        published_date = data['published_date']
        genre = data['genre']

        # connect to the database
        connection, cursor = establish_connection(os.getenv('DB_NAME'))

        # query to insert a new book into the books table
        cursor.execute("INSERT INTO books (title, author, published_date) VALUES (%s, %s, %s);", 
                        (title, author, published_date))

        # close the connection
        close_connection(connection, cursor)

        # return a success message
        return jsonify({"message": "Book added successfully!"}), 201

    except Exception as e:
        return f"An error occurred: {e}"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6000)
