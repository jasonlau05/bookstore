from flask import Flask, jsonify, request
import mysql.connector
from flask_bcrypt import Bcrypt

app = Flask(__name__)
bcrypt = Bcrypt(app)

lines = open('creds.txt').read().splitlines()
DBUSER = lines[0]
DBPASS = lines[1]
DBNAME = lines[2]

DB_CONFIG = {
    'user': DBUSER,
    'password': DBPASS,
    'host': '127.0.0.1',
    'database': DBNAME
}

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        return None

# encryption

def hash_password(password):
    return bcrypt.generate_password_hash(password).decode('utf-8')

def check_password(hashed_password, password_attempt):
    return bcrypt.check_password_hash(hashed_password, password_attempt)

# api endpoints

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password_attempt = data.get('password')

        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Database unavailable'}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT UserID, UserName, Email, Manager, Password FROM Users WHERE UserName = %s"
        cursor.execute(query, (username,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            return jsonify({'message': 'Invalid credentials'}), 401

        try:
            ok = check_password(user['Password'], password_attempt)
        except Exception as e:
            return jsonify({'message': 'Password check failed', 'error': str(e)}), 500

        if not ok:
            return jsonify({'message': 'Invalid credentials'}), 401

        token = str(user['UserID'])
        return jsonify({
            'success': True,
            'message': f"Welcome, {user['Email']}!",
            'token': token,
            'user_id': user['UserID'],
            'username': user['UserName'],
            'email': user['Email'],
            'manager': user['Manager']
        }), 200

    except Exception as e:
        # catch anything unexpected and return JSON so frontend doesn't crash
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500

@app.route('/books', methods=['GET'])
def get_books():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)

    # Read ?query= from URL
    search_query = request.args.get("query")

    query = """
        SELECT BookID, Name, Author, Buyprice, Rentprice, Status
        FROM Books
        WHERE 1 = 1
    """
    params = []

    if search_query:
        query += " AND (Name LIKE %s OR Author LIKE %s)"
        pattern = f"%{search_query}%"
        params.extend([pattern, pattern])

    cursor.execute(query, params)
    books = cursor.fetchall()
    conn.close()

    return jsonify(books), 200

@app.route('/book', methods=['POST'])
def add_book():
    data = request.get_json()
    name = data.get('name')
    author = data.get('author')
    buy_price = data.get('buy_price')
    rent_price = data.get('rent_price')
    status='in stock'
    auth_token = request.headers.get('Authorization') # Simple check

    # In a real app, we'd validate the token and check user permissions.
    # For this demo, we check if the token exists (i.e., user logged in).
    if not auth_token:
        return jsonify({'message': 'Authorization required'}), 403

    if not all([name, author, buy_price, rent_price]):
        return jsonify({'message': 'Missing book data'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()
    try:
        query = "INSERT INTO Books (Name, Author, Buyprice, Rentprice, Status) VALUES (%s, %s, %s, %s, %s)"
        cursor.execute(query, (name, author, buy_price, rent_price, status))
        conn.commit()
        return jsonify({'message': f'Book "{name}" added successfully!'}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Database error: {err}'}), 500
    finally:
        conn.close()

@app.route('/book/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    data = request.get_json()
    auth_token = request.headers.get('Authorization')

    if not auth_token:
        return jsonify({'message': 'Authorization required'}), 403

    allowed_fields = {
        'name': 'Name',
        'author': 'Author',
        'buyprice': 'Buyprice',
        'rentprice': 'Rentprice',
        'status': 'Status'
    }
    
    set_clauses = []
    update_values = []
    
    for json_key, db_column in allowed_fields.items():
        if json_key in data:
            set_clauses.append(f"{db_column} = %s")
            update_values.append(data[json_key])
            
    if not set_clauses:
        return jsonify({'message': 'No valid update data provided'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()
    try:
        update_values.append(book_id)
        query = "UPDATE Books SET " + ", ".join(set_clauses) + " WHERE BookID = %s"
        
        cursor.execute(query, tuple(update_values))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'message': f'Book ID {book_id} not found.'}), 404
            
        return jsonify({'message': f'Book ID {book_id} updated successfully.'}), 200

    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Database error: {err}'}), 500
    finally:
        conn.close()

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    manager = False

    if not all([email, username, password]):
        return jsonify({'message': 'Missing required fields: email, Username, and Password'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()

    hashed_password = hash_password(password)


    try:
        query = "INSERT INTO Users (UserName, Password, Email, Manager) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (username, hashed_password, email, manager))
        conn.commit()
        return jsonify({'message': f'your account has been created'}), 201
    except mysql.connector.errors.IntegrityError:
        conn.rollback()
        return jsonify({'message': 'username taken. try another'}), 409
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'database broke gangy'}), 500
    finally:
        conn.close()

@app.route('/orders', methods=['GET'])
def get_orders():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)
    query = "SELECT OrderID, CustomerID, TotalCost, Status FROM Orders"
    cursor.execute(query)
    orders = cursor.fetchall()
    conn.close()

    return jsonify(orders), 200

@app.route('/orders/<int:user_id>', methods=['GET'])
def get_myorders(user_id):
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)
    query = "SELECT OrderID, TotalCost, Status FROM Orders where CustomerID = %s"
    cursor.execute(query, (user_id,))
    orders = cursor.fetchall()
    conn.close()

    return jsonify(orders), 200

@app.route('/order/<int:order_id>', methods=['PUT'])
def update_order(order_id):
    data = request.get_json()
    auth_token = request.headers.get('Authorization')

    if not auth_token:
        return jsonify({'message': 'Authorization required'}), 403

    allowed_fields = {
        'status': 'Status'
    }
    
    set_clauses = []
    update_values = []
    
    for json_key, db_column in allowed_fields.items():
        if json_key in data:
            set_clauses.append(f"{db_column} = %s")
            update_values.append(data[json_key])
            
    if not set_clauses:
        return jsonify({'message': 'No valid update data provided'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()
    try:
        update_values.append(order_id)
        query = "UPDATE Orders SET " + ", ".join(set_clauses) + " WHERE OrderID = %s"
        
        cursor.execute(query, tuple(update_values))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({'message': f'Book ID {order_id} not found.'}), 404
            
        return jsonify({'message': f'Book ID {order_id} updated successfully.'}), 200

    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Database error: {err}'}), 500
    finally:
        conn.close()

@app.route('/orderitems/<int:order_id>', methods=['GET'])
def get_orderitems(order_id):
    auth_token = request.headers.get('Authorization')
    if not auth_token:
        return jsonify({'message': 'Authorization required'}), 403

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)

    try:
        query = """
            SELECT 
                oi.ItemID AS BookID,
                oi.OrderType,
                b.Name AS Title,
                CASE 
                    WHEN oi.OrderType = 'buy' THEN b.Buyprice
                    WHEN oi.OrderType = 'rent' THEN b.Rentprice
                    ELSE NULL
                END AS Price
            FROM OrderItems oi
            JOIN Books b ON oi.ItemID = b.BookID
            WHERE oi.OrderID = %s
        """

        cursor.execute(query, (order_id,))
        order_items = cursor.fetchall()

        if not order_items:
            return jsonify({'message': f'No items found for Order ID {order_id}.'}), 404

        return jsonify(order_items), 200

    except Exception as err:
        print(f"Error fetching order items: {err}")
        return jsonify({'message': f'Server error: {err}'}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/order', methods=['POST'])
def create_order():
    data = request.get_json()
    auth_token = request.headers.get('Authorization')
    
    if not auth_token:
        return jsonify({'message': 'Authorization required'}), 403
    
    user_id = data.get('user_id')
    items = data.get('items')
    
    if not user_id or not items:
        return jsonify({'message': 'Missing user_id or items list in payload'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()
    total_cost = 0.0

    try:
        for item in items:
            total_cost += item['price']

        order_query = "INSERT INTO Orders (CustomerID, TotalCost, Status) VALUES (%s, %s, %s)"
        cursor.execute(order_query, (user_id, total_cost, 'pending'))
        order_id = cursor.lastrowid

        if not order_id:
            raise Exception("Could not retrieve OrderID after insertion.")

        # intsert and update status
        for item in items:
            book_id = item['book_id']
            price = item['price']
            transaction = item['type']
            
            # insert
            item_query = "INSERT INTO OrderItems (OrderID, ItemID, OrderType, Price) VALUES (%s, %s, %s, %s)"
            cursor.execute(item_query, (order_id, book_id, transaction, price))
            
            # update status
            if transaction == 'rent':
                status_query = "UPDATE Books SET Status = 'rented' WHERE BookID = %s"
                cursor.execute(status_query, (book_id,))
            if transaction == 'buy':
                status_query = "UPDATE Books SET Status = 'sold' WHERE BookID = %s"
                cursor.execute(status_query, (book_id,))
            
        conn.commit()
        return jsonify({'message': 'Order successfully placed.', 'order_id': order_id, 'total_cost': total_cost}), 201

    except mysql.connector.Error as err:
        conn.rollback()
        print(f"Database error during order creation: {err}")
        return jsonify({'message': f'Database error: {err}'}), 500
        
    except Exception as err:
        conn.rollback()
        return jsonify({'message': f'Server error: {err}'}), 500
        
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    print("Starting Flask API Server on http://127.0.0.1:5000...")
    app.run(debug=True, port=5000)