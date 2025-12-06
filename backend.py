from flask import Flask, jsonify, request
import mysql.connector
from flask_bcrypt import Bcrypt
import jwt
import datetime
from functools import wraps

app = Flask(__name__)
bcrypt = Bcrypt(app)

DB_CONFIG = {
    'user': 'root',
    'password': 'pass',
    'host': '127.0.0.1',
    'database': 'bookstore'
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

SECRET_KEY = "thisisunhackable123"

def check_password(hashed_password, password_attempt):
    return bcrypt.check_password_hash(hashed_password, password_attempt)

def require_auth(manager_only=False, customer_only=False):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                return jsonify({"message": "Authorization required"}), 403

            # token
            if not auth_header.startswith("Bearer "):
                return jsonify({"message": "Invalid token format"}), 401

            # extract jwt
            token = auth_header.split(" ")[1]

            try:
                decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return jsonify({"message": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"message": "Invalid token"}), 401

            # access control
            if manager_only and not decoded.get("manager"):
                return jsonify({"message": "managers only"}), 403

            if customer_only and decoded.get("manager"):
                return jsonify({"message": "customers only"}), 403

            request.user = decoded
            return f(*args, **kwargs)
        return wrapper
    return decorator

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

       
        payload = {
            "user_id": user["UserID"],
            "username": user["UserName"],
            "manager": user["Manager"],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=6)
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

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
@require_auth()
def get_books():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)

    # read query, genre, or year from URL
    search_query = request.args.get("query")
    genre_filter = request.args.get("genre")
    year_filter = request.args.get("year")

    query = """
        SELECT BookID, Name, Author, Buyprice, Rentprice, Status, Quantity, Genre, PublicationYear
        FROM Books
        WHERE 1 = 1
    """
    params = []

    if search_query:
        query += " AND (Name LIKE %s OR Author LIKE %s)"
        pattern = f"%{search_query}%"
        params.extend([pattern, pattern])

    if genre_filter:
        query += " AND Genre = %s"
        params.append(genre_filter)

    if year_filter:
        try:
            int(year_filter)
            query += " AND PublicationYear = %s"
            params.append(year_filter)
        except ValueError:
            pass

    cursor.execute(query, params)
    books = cursor.fetchall()
    conn.close()

    return jsonify(books), 200

@app.route('/book', methods=['POST'])
@require_auth(manager_only=True)
def add_book():
    data = request.get_json()
    name = data.get('name')
    author = data.get('author')
    buy_price = data.get('buy_price')
    rent_price = data.get('rent_price')
    genre = data.get('genre')
    publication_year = data.get('publication_year')
    status='in stock'
    quantity = data.get('quantity')

    if not all([name, author, buy_price, rent_price]):
        return jsonify({'message': 'Missing book data'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()
    try:
        query = "INSERT INTO Books (Name, Author, Buyprice, Rentprice, Status, Quantity, Genre, PublicationYear) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (name, author, buy_price, rent_price, status, quantity, genre, publication_year))
        conn.commit()
        return jsonify({'message': f'Book "{name}" added successfully!'}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Database error: {err}'}), 500
    finally:
        conn.close()

@app.route('/book/<int:book_id>', methods=['PUT'])
@require_auth(manager_only=True)
def update_book(book_id):
    data = request.get_json()

    allowed_fields = {
        'name': 'Name',
        'author': 'Author',
        'buyprice': 'Buyprice',
        'rentprice': 'Rentprice',
        'status': 'Status',
        'quantity': 'Quantity',
        'genre': 'Genre',
        'publicationyear': 'PublicationYear'
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
@require_auth(manager_only=True)
def get_orders():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)
    query = """
            SELECT 
                Orders.OrderID,
                Orders.CustomerID,
                Users.UserName AS CustomerName,
                Orders.TotalCost,
                Orders.Status
            FROM Orders
            INNER JOIN Users ON Orders.CustomerID = Users.UserID
        """
    cursor.execute(query)
    orders = cursor.fetchall()
    conn.close()

    return jsonify(orders), 200

@app.route('/orders/<int:user_id>', methods=['GET'])
@require_auth(customer_only=True)
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
@require_auth(manager_only=True)
def update_order(order_id):
    data = request.get_json()

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
@require_auth()
def get_orderitems(order_id):

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
                    WHEN oi.OrderType IN ('rent', 'returned') THEN b.Rentprice
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
@require_auth(customer_only=True)
def create_order():
    data = request.get_json()
    
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

            # reduce quantity
            qty_query = "UPDATE Books SET Quantity = Quantity - 1 WHERE BookID = %s AND Quantity > 0"
            cursor.execute(qty_query, (book_id,))
            
            # insert
            item_query = "INSERT INTO OrderItems (OrderID, ItemID, OrderType, Price) VALUES (%s, %s, %s, %s)"
            cursor.execute(item_query, (order_id, book_id, transaction, price))

            
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

@app.route('/profile/<int:user_id>', methods=['GET'])
@require_auth(customer_only=True)
def get_profile(user_id):
    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    
    try:
        query = """
        SELECT
            COUNT(OrderID) AS TotalOrders,
            SUM(TotalCost) AS TotalSpent
        FROM Orders WHERE CustomerID = %s;
        """
        
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()

        if result and result['TotalOrders'] is not None:
            # Successfully retrieved data
            total_orders = int(result['TotalOrders'])
            # Ensure TotalSpent is a float, defaulting to 0.00 if NULL
            total_spent = float(result['TotalSpent']) if result['TotalSpent'] is not None else 0.00
            
            # You could add other profile data here, e.g.,
            # fetch user details from a separate Users table.
            
            profile_data = {
                "CustomerID": user_id,
                "TotalOrders": total_orders,
                # Format TotalSpent to two decimal places for currency
                "TotalSpent": f"{total_spent:.2f}", 
                # Placeholder for AccountCreated, which you might fetch later
                "AccountCreated": "2023-01-01" 
            }
            
            return jsonify(profile_data), 200
        else:
            # User has no completed orders yet
            return jsonify({
                "CustomerID": user_id,
                "TotalOrders": 0,
                "TotalSpent": "0.00",
                "AccountCreated": "N/A"
            }), 200


    except mysql.connector.Error as err:
        print(f"Database query error: {err}")
        return jsonify({"message": f"An error occurred during data retrieval: {err}"}), 500
        
    finally:
        # Close the cursor and connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/rating/<int:book_id>', methods=['GET'])
@require_auth(customer_only=True)
def get_ratings(book_id):
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor(dictionary=True)
    query = "SELECT Rating, Comments FROM Ratings where BookID = %s"
    cursor.execute(query, (book_id,))
    orders = cursor.fetchall()
    conn.close()

    return jsonify(orders), 200

@app.route('/rating', methods=['POST'])
@require_auth(customer_only=True)
def create_rating():
    data = request.get_json()

    book_id = data.get('book_id')
    customer_id = data.get('customer_id')
    rating = data.get('rating')
    comments = data.get('comments', '')

    if not all([book_id, customer_id, rating]):
        return jsonify({'message': 'Missing required fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
    INSERT INTO Ratings (BookID, CustomerID, Rating, Comments)
    VALUES (%s, %s, %s, %s)
    """
    cursor.execute(query, (book_id, customer_id, rating, comments))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Review submitted successfully'}), 201

@app.route('/rating/<int:book_id>', methods=['PUT'])
@require_auth(customer_only=True)
def update_rating(book_id):
    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor()

    # check if record exists
    cursor.execute("SELECT 1 FROM Ratings WHERE BookID = %s", (book_id,))
    exists = cursor.fetchone()

    if exists:
        # UPDATE existing
        query = "UPDATE Ratings SET Rating = %s, Comments = %s WHERE BookID = %s"
        cursor.execute(query, (data['rating'], data['comments'], book_id))
    else:
        # INSERT new
        query = "INSERT INTO Ratings (BookID, Rating, Comments) VALUES (%s, %s, %s)"
        cursor.execute(query, (book_id, data['rating'], data['comments']))

    conn.commit()
    conn.close()
    return jsonify({'message': 'Review saved.'}), 201

@app.route('/orderitem/<int:item_id>', methods=['PUT'])
@require_auth(manager_only=True)
def returned(item_id):
    data = request.get_json()

    if 'ordertype' not in data:
        return jsonify({'message': 'Missing ordertype field'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Database unavailable'}), 500

    cursor = conn.cursor()

    try:
        query = """
            UPDATE OrderItems 
            SET OrderType = %s 
            WHERE ItemID = %s
        """

        cursor.execute(query, (data['ordertype'], item_id))

        if cursor.rowcount == 0:
            return jsonify({
                'message': f'No rental order for Book ID {book_id} found.'
            }), 404

        return_stock = """
            UPDATE Books 
            SET Quantity = Quantity + 1
            WHERE BookID = %s
        """
        cursor.execute(return_stock, (item_id,))

        conn.commit()

        return jsonify({'message': 'Order marked as returned'}), 200
    
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({'message': f'Database error: {err}'}), 500
    
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting Flask API Server on http://127.0.0.1:5000...")
    app.run(debug=True, port=5000)