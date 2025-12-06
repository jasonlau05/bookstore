import mysql.connector

DB_CONFIG = {
    'user': 'root',
    'password': 'pass',
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
    Status varchar(50) not null,
    Quantity int not null,
    Genre varchar(100) not null,
    PublicationYear int not null
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

create table Ratings (
    RatingID int auto_increment primary key,
    CustomerID int not null,
    BookID int not null,
    Rating int not null,
    Comments varchar(255)
);

INSERT INTO Users (UserName, Password, Email, Manager) VALUES
('admin', '$2b$12$p4hMGKZ.YuzAyX73DgqbP.9rISmVz3ljkNSuZFRmJGCuzRBPp/bIu', 'Jason', TRUE),
('eric', '$2b$12$0HSurjZan.kVEE0.JyLVxes9r85l89NYxuprrj/4WyoeYtSzlSrI2', 'eric@gmail.com', FALSE);

insert into Books (Name, Author, Buyprice, Rentprice, Status, Quantity, Genre, PublicationYear) values
('The Great Gatsby', 'F. Scott Fitzgerald', 15.99, 5.00, 'in stock', 67, 'romance', 1978),
('1984', 'George Orwell', 12.50, 4.50, 'rented', 0, 'scifi', 1984),
('To Kill a Mockingbird', 'Harper Lee', 18.00, 6.00, 'sold', 78, 'history', 1927),
('Pride and Prejudice', 'Jane Austen', 10.99, 3.50, 'rented', 21, 'history', 1977),
('The Silent Grove', 'Alicia Rowland', 15.99, 3.99, 'Available', 6, 'mystery', 2018),
('Midnight Over Avalon', 'R. D. Hargrove', 17.50, 4.25, 'Available', 4, 'fantasy', 2020),
('Echoes of Tomorrow', 'Leonard Briggs', 19.00, 4.50, 'Available', 7, 'scifi', 2023),
('Beneath the Iron Sky', 'Clara Henson', 13.75, 3.50, 'Available', 5, 'dystopian', 2016),
('The Crimson Sea', 'James L. Porter', 14.99, 3.99, 'Available', 8, 'adventure', 2017),
('Shadows in the Library', 'Megan Carrow', 12.99, 3.25, 'Available', 10, 'mystery', 2014),
('The Last Frontier', 'H.G. Millard', 21.00, 5.00, 'Unavailable', 0, 'scifi', 2023),
('Garden of Whispers', 'Leah Darrow', 11.50, 2.99, 'Available', 9, 'romance', 2013),
('Wolves of Winterfell', 'Darren Vale', 18.25, 4.50, 'Available', 3, 'fantasy', 2019),
('A Map of Broken Roads', 'T. S. Waller', 16.75, 4.25, 'Available', 6, 'drama', 2022),
('The Unseen Voyage', 'Oliver Avery', 16.99, 4.00, 'Available', 9, 'adventure', 2020),
('Voices from the Attic', 'Marilyn Frost', 11.50, 2.75, 'Available', 10, 'mystery', 2011),
('House of Falling Petals', 'Kimber Leigh', 12.75, 3.10, 'Available', 7, 'romance', 2015),
('Iron Wings', 'Cedric Boone', 18.40, 4.50, 'Available', 4, 'scifi', 2019),
('Secrets of Ashen Wood', 'Nadia Bell', 15.25, 3.60, 'Available', 6, 'fantasy', 2017),
('City Beneath the Waves', 'Harold Linn', 20.50, 5.25, 'Available', 3, 'adventure', 2022),
('Where the Lanterns Fade', 'Arielle Snow', 11.99, 2.99, 'Available', 12, 'drama', 2013),
('Frozen in Amber', 'Tristan Monroe', 14.10, 3.40, 'Unavailable', 0, 'thriller', 2016),
('A Song for Lost Kingdoms', 'Nora Vexley', 17.60, 4.25, 'Available', 6, 'fantasy', 2020),
('The Silver Mirage', 'Gareth Cole', 12.85, 3.20, 'Available', 8, 'mystery', 2014),
('Seas of the Forgotten', 'Dorian Blake', 19.20, 4.80, 'Available', 5, 'adventure', 2021),
('The Willow Wife', 'Emma Holloway', 10.99, 2.50, 'Available', 11, 'drama', 2011),
('The Gravity Paradox', 'Jonas Redd', 21.00, 5.00, 'Available', 4, 'scifi', 2023),
('Echoes from the Deep', 'Marlene Trask', 13.40, 3.25, 'Available', 7, 'mystery', 2017),
('Crimson Horizon', 'Elijah Torrence', 17.90, 4.30, 'Available', 5, 'thriller', 2020),
('The Starlight Market', 'Gareth Cole', 14.75, 3.50, 'Available', 10, 'fantasy', 2018),
('Kings of Broken Steel', 'Harper Quinn', 22.40, 5.60, 'Available', 3, 'scifi', 2022),
('The Secret Orchard', 'Maya DeLorne', 11.60, 2.80, 'Available', 12, 'romance', 2014),
('Beyond the Wanderer’s Path', 'Ivy Marston', 12.50, 3.00, 'Available', 9, 'adventure', 2015);

insert into Orders (CustomerID, TotalCost, Status) values
(1, 50.45, 'pending'),
(2, 434.32, 'pending');

insert into OrderItems (OrderID, ItemID, OrderType, Price) values
(1, 1, 'rent', 67),
(1, 2, 'buy', 69),
(2, 1, 'buy', 10),
(2,100, 'rent', 5.44);

insert into Ratings (CustomerID, BookID, Rating, Comments) values
(1, 1, 4, "this is the best book ever!!11!"),
(2, 1, 2, "what even is this?? I hate it");
"""
    # write to file
    with open("bookstore.sql", "w") as f:
        f.write(sql_content)
        
    setup_database()