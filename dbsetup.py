import mysql.connector

lines = open('creds.txt').read().splitlines()
DBUSER = lines[0]
DBPASS = lines[1]

DB_CONFIG = {
    'user': DBUSER,
    'password': DBPASS,
    'host': '127.0.0.1',
    'raise_on_warnings': True
}

def setup_database(sql_script_path="bookstore.sql"):
    """connects to mysql, drops/creates the database, executes sql script."""
    print("connecting to mysql server")
    conn = None
    try:
        # Connect to MySQL (without specifying a database initially)
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 2. Drop and Create the Database
        print("drop and create db")
        
        # We handle the potential "Can't drop database" warning/error separately
        try:
            cursor.execute("DROP DATABASE IF EXISTS bookstore;")
        except mysql.connector.errors.DatabaseError as db_err:

            print(f"drop failed: {db_err}")

        cursor.execute("CREATE DATABASE bookstore;")
        conn.database = "bookstore" # Switch to the new database
        
        # 3. Execute SQL Script Content
        print(f"executing sql queries")
        
        # Reconstruct the SQL commands
        with open(sql_script_path, 'r') as f:
            # Read the file content provided by the user (which includes the table definitions)
            sql_file = f.read()
        
        sql_commands = [cmd.strip() for cmd in sql_file.split(';') if cmd.strip() and not cmd.strip().upper().startswith(('DROP DATABASE', 'CREATE DATABASE', 'USE'))]

        for command in sql_commands:
            try:
                cursor.execute(command)
            except mysql.connector.Error as err:
                print(f"execute failed: {err}")
                print(f"command: {command}")
                
        conn.commit()
        print("success")
        
    except mysql.connector.Error as err:

        if err.errno == 2003:
            print(f"connect failed: {err.errno}")
        else:
            print(f"error: {err}")
            
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":

    sql_content = """DROP DATABASE IF EXISTS bookstore;
CREATE DATABASE bookstore;
USE bookstore;

CREATE TABLE Users (
    UserID INT AUTO_INCREMENT PRIMARY KEY,
    UserName VARCHAR(50) UNIQUE NOT NULL,
    Password VARCHAR(255) NOT NULL,
    Email VARCHAR(255) UNIQUE NOT NULL,
    Manager boolean NOT NULL
);

CREATE TABLE Books (
    BookID INT auto_increment PRIMARY KEY,
    Name VARCHAR(255) NOT NULL,
    Author varchar(255) not null,
    Buyprice DECIMAL(10,2) NOT NULL,
    Rentprice decimal(10,2) not null,
    Status varchar(50) not null
);

CREATE TABLE Orders (
    OrderID int auto_increment primary key,
    CustomerID int not null,
    TotalCost DECIMAL(10,2),
    Status varchar(10) not null
);

create table OrderItems (
    OrderID int,
    ItemID int not null,
    OrderType varchar(10) not null,
    Price decimal(10,2) not null
);

INSERT INTO Users (UserName, Password, Email, Manager) VALUES
('admin', '$2b$12$p4hMGKZ.YuzAyX73DgqbP.9rISmVz3ljkNSuZFRmJGCuzRBPp/bIu', 'Jason', TRUE),
('nimda', '$2b$12$0HSurjZan.kVEE0.JyLVxes9r85l89NYxuprrj/4WyoeYtSzlSrI2', 'eric', FALSE);

insert into Books (Name, Author, Buyprice, Rentprice, Status) values
('The Great Gatsby', 'F. Scott Fitzgerald', 15.99, 5.00, 'in stock'),
('1984', 'George Orwell', 12.50, 4.50, 'rented'),
('To Kill a Mockingbird', 'Harper Lee', 18.00, 6.00, 'sold'),
('Pride and Prejudice', 'Jane Austen', 10.99, 3.50, 'rented');

insert into Orders (CustomerID, TotalCost, Status) values
(1, 50.45, 'pending'),
(2, 434.32, 'pending');

insert into OrderItems (OrderID, ItemID, OrderType, Price) values
(1, 1, 'rent', 67),
(1, 2, 'buy', 69),
(2,1, 'buy', 10),
(2,100, 'rent', 5.44);
"""
    # write to file
    with open("bookstore.sql", "w") as f:
        f.write(sql_content)
        
    setup_database()