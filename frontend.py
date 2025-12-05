import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from functools import partial
import threading

API_BASE_URL = "http://127.0.0.1:5000"

class BookstoreApp(tk.Tk):
    # main app
    def __init__(self):
        super().__init__()
        self.title("bookstore")
        self.geometry("800x600")
        
        # internal states
        self.user_token = None
        self.user_id = None
        self.username = None
        self.user_email = None
        self.shopping_cart = {}
        
        # container frame
        self.container = ttk.Frame(self)
        self.container.pack(side="top", fill="both", expand=True, padx=10, pady=10)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.manager = None
        
        self.frames = {}
        self.show_frame(MainLoginSelector)

    def show_frame(self, frame_class, **kwargs):
        # destroye existing
        for frame in self.frames.values():
            frame.destroy()
        self.frames = {}
            
        # create frame
        frame = frame_class(self.container, self, **kwargs)
        self.frames[frame_class] = frame
        
        # display
        frame.grid(row=0, column=0, sticky="nsew")
        frame.tkraise()

    def set_auth_token(self, token, username=None, email=None):
        self.user_token = token
        self.username = username
        self.user_email = email

    def get_auth_token(self):
        if not self.user_token:
            print("Warning: Attempted to get auth token when none was set.")
        return self.user_token

    def addcart(self, book_data, transaction_type):
        book_id = book_data['BookID']
        
        if book_id in self.shopping_cart:
            return False 

        if transaction_type == 'buy':
            price_key = 'BuyPrice'
        else:
            price_key = 'RentPrice'
        
        price_str = book_data.get(price_key, '$0.00').replace('$', '')
        
        self.shopping_cart[book_id] = {
            'book_id': book_id,
            'title': book_data['Title'],
            'price': float(price_str),
            'type': transaction_type
        }
        return True

    def get_cart_items(self):
        return list(self.shopping_cart.values())

    def clear_cart(self):
        self.shopping_cart = {}

    def run_async(self, func, callback=None):
        def worker():
            result = None
            error = None
            try:
                result = func()
            except Exception as e:
                error = e

            # safe update on main thread
            self.after(0, lambda: callback(result, error) if callback else None)

        threading.Thread(target=worker, daemon=True).start()

class CustomerLoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="customer login", font=("Arial", 18, "bold")).pack(pady=20)
        
        frame = ttk.Frame(self)
        frame.pack(pady=10)

        ttk.Label(frame, text="Username").grid(row=0, column=0, pady=5)
        self.username_entry = ttk.Entry(frame)
        self.username_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="Password").grid(row=1, column=0, pady=5)
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)

        ttk.Button(self, text="Login", command=self.login).pack(pady=10)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame(MainLoginSelector)).pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        def task():
            return requests.post(
            f"{API_BASE_URL}/login",
            json={"username": username, "password": password}
        )

        def done(response, error):
            if response.status_code == 200:
                data = response.json()
                if data["manager"]:
                    messagebox.showerror("Error", "invalid credentials")
                    return

                self.controller.set_auth_token(
                    data["token"],
                    username=data["username"],
                    email=data["email"]
                )
                self.controller.user_id = data["user_id"]
                self.controller.manager = data["manager"]


                self.controller.show_frame(CustomerDashboardFrame)
            else:
                messagebox.showerror("Login Failed", response.json().get("message"))

        self.controller.run_async(task, done)

class ManagerLoginFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="Manager Login", font=("Arial", 18, "bold")).pack(pady=20)
        
        frame = ttk.Frame(self)
        frame.pack(pady=10)

        ttk.Label(frame, text="Username").grid(row=0, column=0, pady=5)
        self.username_entry = ttk.Entry(frame)
        self.username_entry.grid(row=0, column=1, pady=5)

        ttk.Label(frame, text="Password").grid(row=1, column=0, pady=5)
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.grid(row=1, column=1, pady=5)

        ttk.Button(self, text="Login", command=self.login).pack(pady=10)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame(MainLoginSelector)).pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        def task():
            return requests.post(
                f"{API_BASE_URL}/login",
                json={"username": username, "password": password}
            )

        def done(response, error):
            if response.status_code == 200:
                data = response.json()

                if not data['manager']:
                    messagebox.showerror("Error", "invalid credentials")
                    return

                self.controller.set_auth_token(
                    data["token"],
                    username=data["username"],
                    email=data["email"]
                )
                self.controller.user_id = data["user_id"]
                self.controller.manager = data["manager"]


                self.controller.show_frame(ManagerDashboardFrame)

            else:
                messagebox.showerror("Login Failed", response.json().get("message"))

        self.controller.run_async(task, done)

class RegisterFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Title
        ttk.Label(self, text="create new account", font=('Arial', 18, 'bold')).pack(pady=20)

        register_block = ttk.Frame(self, padding="20 20 20 20", relief="raised")
        register_block.pack(pady=30, padx=50)

        fields = [("Email:", "email"), ("Username:", "username"), ("Password:", "password")]
        self.entries = {}

        for i, (label_text, key) in enumerate(fields):
            ttk.Label(register_block, text=label_text).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            show_char = "*" if key == "password" else ""
            entry = ttk.Entry(register_block, width=30, show=show_char)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[key] = entry

        # Register Button
        register_button = ttk.Button(register_block, text="register", command=self.submit_registration)
        register_button.grid(row=len(fields), column=0, columnspan=2, pady=(15, 5))

        # Cancel Button
        cancel_button = ttk.Button(register_block, text="back to login", 
                                   command=lambda: controller.show_frame(MainLoginSelector))
        cancel_button.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(5, 15))

    def submit_registration(self):        
        new_user = {
            'email': self.entries['email'].get(),
            'username': self.entries['username'].get(),
            'password': self.entries['password'].get()
        }
        
        # Basic validation
        if not all(new_user.values()):
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:

            def task():
                return requests.post(
                    f"{API_BASE_URL}/register",
                    json=new_user
                )
            
            def done(response, error):
                data = response.json()
                if response.status_code == 201:
                    messagebox.showinfo("new account", data.get('message', 'your account has been created'))
                    # Go back to login screen after successful registration
                    self.controller.show_frame(MainLoginSelector)
                else:
                    messagebox.showerror("Failure", data.get('message', 'failed. username could be taken.'))

            self.controller.run_async(task, done)

        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the Flask server. Is api_server.py running?")

class BookListFrame(ttk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # headers
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(header_frame, text="book inventory", font=('Arial', 16, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="logout", command=self.logout).pack(side='right', padx=5)
        ttk.Button(header_frame, text="add new book", command=lambda: controller.show_frame(AddBookFrame)).pack(side='right', padx=5)
        ttk.Button(header_frame, text="edit book", command=self.edit_book).pack(side='right', padx=5)
        ttk.Button(header_frame, text="back", command=lambda: controller.show_frame(ManagerDashboardFrame)).pack(side='right', padx=5)


        # Treeview
        self.tree = ttk.Treeview(self, columns=("ID", 'Title', 'Author', 'BuyPrice', 'RentPrice', 'Status', 'Quantity'), show='headings')
        self.tree.heading('ID', text='ID')
        self.tree.heading('Title', text='Title')
        self.tree.heading('Author', text='Author')
        self.tree.heading('BuyPrice', text='Buy Price')
        self.tree.heading('RentPrice', text='Rent Price')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Quantity', text='Inventory')
        
        self.tree.column('ID', width=50)
        self.tree.column('Title', width=300)
        self.tree.column('Author', width=200)
        self.tree.column('BuyPrice', width=100)
        self.tree.column('RentPrice', width=100)
        self.tree.column('Status', width=0, stretch=False)
        self.tree.column('Quantity', width = 50)
        
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.load_books()

    def load_books(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        def task():
            return requests.get(f"{API_BASE_URL}/books", headers={'Authorization': f'Bearer {self.controller.get_auth_token()}'})

        def done(response, error):
            if error:
                messagebox.showerror("Network Error", str(error))
                return

            if response.status_code == 200:
                for book in response.json():
                    self.tree.insert("", "end", values=(
                        book["BookID"],
                        book["Name"],
                        book["Author"],
                        book["Buyprice"],
                        book["Rentprice"],
                        book["Status"],
                        book["Quantity"]
                    ))
        
        self.controller.run_async(task, done)

    def edit_book(self):
        selected = self.tree.selection()
        if not selected:
            return

        book_data = self.tree.item(selected[0])["values"]
        self.controller.show_frame(EditBookFrame, book=book_data)
    
    def logout(self):
        self.controller.set_auth_token(None)
        self.controller.show_frame(MainLoginSelector)
  
class AddBookFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # Title
        ttk.Label(self, text="add new book", font=('Arial', 16, 'bold')).pack(pady=20)
        
        form_block = ttk.Frame(self, padding="20 20 20 20", relief="groove")
        form_block.pack(pady=50, padx=50)

        fields = ['Title', 'Author', 'Buy Price', 'Rent Price', 'Quantity']
        self.entries = {}
        
        for i, field in enumerate(fields):
            ttk.Label(form_block, text=f"{field}:").grid(row=i, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(form_block, width=40)
            entry.grid(row=i, column=1, padx=5, pady=5)
            self.entries[field.replace(' ', '_').lower()] = entry
        
        # Buttons
        button_frame = ttk.Frame(form_block)
        button_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)
        
        ttk.Button(button_frame, text="add book", command=self.submit_book).pack(side='left', padx=10)
        ttk.Button(button_frame, text="cancel", command=lambda: controller.show_frame(BookListFrame)).pack(side='left', padx=10)
        
    def submit_book(self):        
        new_book = {
            'name': self.entries['title'].get(),
            'author': self.entries['author'].get(),
            'buy_price': self.entries['buy_price'].get(),
            'rent_price': self.entries['rent_price'].get(),
            'quantity': self.entries['quantity'].get()
        }
        
        # basic validation
        if not all(new_book.values()):
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:
            # Send POST request with Authorization header

            def task():
                return requests.post(
                    f"{API_BASE_URL}/book",
                    headers={'Authorization': f'Bearer {self.controller.user_token}'},
                    json=new_book
                )
            
            def done(response, error):
                if response.status_code == 201:
                    self.controller.show_frame(BookListFrame)
                else:
                    messagebox.showerror("Error", response.json().get('message', 'Failed to add book.'))
            
            self.controller.run_async(task, done)

        except requests.exceptions.ConnectionError:
            messagebox.showerror("Connection Error", "Could not connect to the Flask server.")

class MainLoginSelector(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="jason's bookstore",
                  font=("Arial", 20, "bold")).pack(pady=40)

        ttk.Button(self, text="customer login",
                   command=lambda: controller.show_frame(CustomerLoginFrame),
                   width=30).pack(pady=10)

        ttk.Button(self, text="manager login",
                   command=lambda: controller.show_frame(ManagerLoginFrame),
                   width=30).pack(pady=10)

        ttk.Button(self, text="create account",
                   command=lambda: controller.show_frame(RegisterFrame),
                   width=30).pack(pady=10)

class OrdersFrame(ttk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        # headers
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(header_frame, text="Orders", font=('Arial', 16, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Logout", command=self.logout).pack(side='right', padx=5)
        ttk.Button(header_frame, text="Mark as Paid", command=self.mark_paid).pack(side='right', padx=5)
        ttk.Button(header_frame, text="view order details", command=self.view_details).pack(side='right', padx=5)
        ttk.Button(header_frame, text="back", command=lambda: controller.show_frame(ManagerDashboardFrame)).pack(side='right', padx=5)


        # Treeview
        self.tree = ttk.Treeview(self, columns=("OrderID", 'Customer', 'TotalCost', 'Status'), show='headings')
        self.tree.heading('OrderID', text='Order ID')
        self.tree.heading('Customer', text='Customer ID')
        self.tree.heading('TotalCost', text='Total Cost')
        self.tree.heading('Status', text='Status')
        
        self.tree.column('OrderID', width=50)
        self.tree.column('Customer', width=50)
        self.tree.column('TotalCost', width=200)
        self.tree.column('Status', width=50)
        
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)

        self.load_orders()

        def mark_paid(self):
            selected = self.tree.selection()
            if not selected:
                return

            order_id = self.tree.item(selected[0])["values"][0]

            requests.put(f"{API_BASE_URL}/order/{order_id}",
                        json={"status": "paid"})

            self.load_orders()

    def load_orders(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        response = requests.get(f"{API_BASE_URL}/orders", headers={'Authorization': f'Bearer {self.controller.get_auth_token()}'})
        if response.status_code == 200:
            for order in response.json():
                self.tree.insert("", "end", values=(
                    order["OrderID"],
                    order["CustomerID"],
                    order["TotalCost"],
                    order["Status"]
                ))
    
    def logout(self):
        self.controller.set_auth_token(None)
        self.controller.show_frame(MainLoginSelector)

    def mark_paid(self):
        selected = self.tree.selection()
        if not selected:
            return

        selected_item_values = self.tree.item(selected[0])["values"]
        
        order_id = selected_item_values[0]

        if not selected_item_values[3] == 'pending':
            return
        
        auth_header_value = self.controller.get_auth_token()
        if not auth_header_value:
            messagebox.showerror("Error", "User not logged in or token expired.")
            return

        headers = {
            'Authorization': f'Bearer {auth_header_value}',
            'Content-Type': 'application/json'
        }

        try:
            def task():
                return requests.put(
                    f"{API_BASE_URL}/order/{order_id}", 
                    json={"status": "paid"},
                    headers=headers
                )

            def done(response, error):
                if response.status_code == 200:
                    self.load_orders()
                else:
                    # Handle API errors
                    error_message = response.json().get('message', 'Unknown API Error')
                    messagebox.showerror("Error", f"Failed to update status for Book ID {order_id}. Status: {response.status_code}. Message: {error_message}")
            
            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")
    
    def view_details(self):
        selected = self.tree.selection()
        if not selected:
            return

        selected_item_values = self.tree.item(selected[0])["values"]
        order_id = selected_item_values[0]

        try:
            auth_header_value = self.controller.get_auth_token()
            if not auth_header_value:
                messagebox.showerror("Authorization Error", "User token not available.")
                return

            headers = {'Authorization': f'Bearer {auth_header_value}', 'Content-Type': 'application/json'}

            def task():
                return requests.get(f"{API_BASE_URL}/orderitems/{order_id}", headers=headers)

            def done(response, error):
                if response.status_code == 200:
                    order_items = response.json()
                    
                    # success case
                    self.controller.show_frame(OrderDetailsFrame, order_id=order_id, items=order_items)

                else:
                    error_message = f"Status: {response.status_code}"
                    try:
                        data = response.json()
                        error_message += f". Message: {data.get('message', 'Unknown API Error')}"
                    except requests.exceptions.JSONDecodeError:
                        if response.text:
                            error_message += f". Response: {response.text[:100]}..."
                        else:
                            error_message += ". (No response body received)"

                    messagebox.showerror("API Error", f"Failed to fetch order items. {error_message}")
                
            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")

class MyOrdersFrame(ttk.Frame):

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.data_labels = {}

        # header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(header_frame, text="my profile", font=('Arial', 16, 'bold')).pack(side='left')
        ttk.Button(header_frame, text="Logout", command=self.logout).pack(side='right', padx=5)
        ttk.Button(header_frame, text="view order details", command=self.view_details).pack(side='right', padx=5)
        ttk.Button(header_frame, text="back", command=lambda: controller.show_frame(CustomerDashboardFrame)).pack(side='right', padx=5)

        stats_frame = ttk.Frame(self)
        stats_frame.pack(fill='x', padx=20, pady=5) 
        
        # total orders
        ttk.Label(stats_frame, text="total orders:").pack(side='left', padx=(0, 5))
        orders_label = ttk.Label(stats_frame)
        orders_label.pack(side='left', padx=(0, 20))
        self.data_labels["total_orders"] = orders_label

        # total spent
        ttk.Label(stats_frame, text="total spent:").pack(side='left', padx=(0, 5))
        spent_label = ttk.Label(stats_frame)
        spent_label.pack(side='left')
        self.data_labels["total_spent"] = spent_label
        
        # Treeview
        self.tree = ttk.Treeview(self, columns=("OrderID", 'TotalCost', 'Status'), show='headings')
        self.tree.heading('OrderID', text='Order ID')
        self.tree.heading('TotalCost', text='Total Cost')
        self.tree.heading('Status', text='Status')
        
        self.tree.column('OrderID', width=50)
        self.tree.column('TotalCost', width=200)
        self.tree.column('Status', width=0, stretch=False)
        
        self.tree.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.load_orders()
        self.load_userdata()

    def load_orders(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        user_id = self.controller.user_id

        def task():
            return requests.get(f"{API_BASE_URL}/orders/{user_id}", headers={'Authorization': f'Bearer {self.controller.get_auth_token()}'})

        def done(response, error):
            if response.status_code == 200:
                for order in response.json():
                    self.tree.insert("", "end", values=(
                        order["OrderID"],
                        order["TotalCost"],
                        order["Status"]
                    ))
        
        self.controller.run_async(task, done)
    
    def load_userdata(self):
        user_id = self.controller.user_id
            
        try:
            # Use an endpoint that returns profile summary data
            def task():
                return requests.get(f"{API_BASE_URL}/profile/{user_id}", headers = {'Authorization': f'Bearer {self.controller.get_auth_token()}'}) 
            
            def done(response, error):
                if response.status_code == 200:
                    profile_data = response.json()
                    
                    # Update the labels with fetched data
                    self.data_labels["total_orders"].config(text=str(profile_data.get("TotalOrders", 0)))
                    
                    # Format currency nicely
                    spent = float(profile_data.get("TotalSpent", 0.00))
                    self.data_labels["total_spent"].config(text=f"${spent:,.2f}")
                            
                else:
                    for key in self.data_labels:
                        self.data_labels[key].config(text="Error fetching data")
                    print(f"Error: API returned status code {response.status_code}")

            self.controller.run_async(task, done)
                
        except requests.exceptions.RequestException as e:
            for key in self.data_labels:
                self.data_labels[key].config(text="Connection Error")
            print(f"Error connecting to API: {e}")

    def logout(self):
        """Clears auth token and returns to the login screen."""
        self.controller.set_auth_token(None)
        self.controller.show_frame(MainLoginSelector)

    def load_profile_data(self):
        user_id = self.controller.user_id
        
        for key in self.data_labels:
            self.data_labels[key].config(text="Loading...")
            
        try:

            def task():
                return requests.get(f"{API_BASE_URL}/profile/{user_id}", headers = {'Authorization': f'Bearer {auth_header_value}'}) 
            
            def done(response, error):
                if response.status_code == 200:
                    
                    profile_data = response.json()

                    orders = profile_data.get("TotalOrders", 0)
                    self.data_labels["total_orders"].config(text=str(orders))
                    
                    spent = profile_data.get("TotalSpent", "0.00")
                    self.data_labels["total_spent"].config(text=f"${spent}") 
                    
                else:
                    error_msg = f"API Error: {response.status_code}"
                    for key in self.data_labels:
                        self.data_labels[key].config(text=error_msg)
                    print(error_msg, response.text)

            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            conn_error = "Connection Error"
            for key in self.data_labels:
                self.data_labels[key].config(text=conn_error)
            print(f"Error connecting to API: {e}")

    def view_details(self):
        selected = self.tree.selection()
        if not selected:
            return

        selected_item_values = self.tree.item(selected[0])["values"]
        order_id = selected_item_values[0]

        try:
            auth_header_value = self.controller.get_auth_token()
            if not auth_header_value:
                messagebox.showerror("Authorization Error", "User token not available.")
                return

            headers = {'Authorization': f'Bearer {auth_header_value}', 'Content-Type': 'application/json'}

            def task():
                return requests.get(f"{API_BASE_URL}/orderitems/{order_id}", headers=headers)
            def done(response, error):
                if response.status_code == 200:
                    order_items = response.json()
                    
                    # Success: Pass data to the new frame and switch view
                    self.controller.show_frame(MyOrderDetailsFrame, order_id=order_id, items=order_items)

                else:
                    # Handle API errors (403, 404, 500) gracefully
                    error_message = f"Status: {response.status_code}"
                    try:
                        data = response.json()
                        error_message += f". Message: {data.get('message', 'Unknown API Error')}"
                    except requests.exceptions.JSONDecodeError:
                        if response.text:
                            error_message += f". Response: {response.text[:100]}..."
                        else:
                            error_message += ". (No response body received)"

                    messagebox.showerror("API Error", f"Failed to fetch order items. {error_message}")
            self.controller.run_async(task, done)
                
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")

class EditBookFrame(ttk.Frame):
    def __init__(self, parent, controller, book=None):
        super().__init__(parent)
        self.controller = controller
        self.book = book

        # unpack
        book_id, title, author, buy, rent, status, quantity = book

        ttk.Label(self, text=f"Edit Book Info (ID: {book_id})", font=("Arial", 18, "bold")).pack(pady=20)

        frame = ttk.Frame(self)
        frame.pack()

        self.entries = {}
        fields = [("Title", title), ("Author", author),
                  ("Buy Price", buy), ("Rent Price", rent), ("Quantity", quantity)]

        for i, (label, value) in enumerate(fields):
            ttk.Label(frame, text=label).grid(row=i, column=0, pady=5, sticky='w')
            entry = ttk.Entry(frame, width=40)
            entry.insert(0, value)
            entry.grid(row=i, column=1, pady=5, padx=10)
            self.entries[label] = entry

        ttk.Button(self, text="Save Changes", command=self.save).pack(pady=15)
        ttk.Button(self, text="Back", command=lambda: controller.show_frame(BookListFrame)).pack()

        self.book_id = book_id

    def save(self):
        data = {
            "name": self.entries["Title"].get(),
            "author": self.entries["Author"].get(),
            "buyprice": self.entries["Buy Price"].get(),
            "rentprice": self.entries["Rent Price"].get(),
            "quantity": self.entries["Quantity"].get()
        }

        # get auths
        try:
            auth_token = self.controller.get_auth_token()
        except AttributeError:
            messagebox.showerror("Authentication Error", "Controller must implement get_auth_token(). Cannot save.")
            return

        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        
        # validation
        if not all(data.values()):
            messagebox.showerror("Validation Error", "All fields must be filled.")
            return

        # request
        try:
            def task():
                return requests.put(
                    f"{API_BASE_URL}/book/{self.book_id}", 
                    json=data,
                    headers=headers
                )
            
            # response
            def done(response, error):
                if response.status_code == 200:
                    self.controller.show_frame(BookListFrame)
                elif response.status_code == 403:
                    messagebox.showerror("Authorization Failed", "You do not have permission to edit books.")
                elif response.status_code == 404:
                    messagebox.showerror("Not Found", f"Book ID {self.book_id} was not found on the server.")
                else:
                    error_message = response.json().get('message', 'Unknown API Error')
                    messagebox.showerror("API Error", f"Failed to save changes. Status {response.status_code}: {error_message}")

            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")

class CustomerDashboardFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="customer dashboard",
                  font=("Arial", 20, "bold")).pack(pady=30)

        ttk.Button(self, text="my profile",
                   command=lambda: controller.show_frame(MyOrdersFrame),
                   width=30).pack(pady=10)

        ttk.Button(self, text="browse books",
                   command=lambda: controller.show_frame(CustomerSearchFrame),
                   width=30).pack(pady=10)

        ttk.Button(self, text="logout",
                   command=self.logout,
                   width=30).pack(pady=10)
    
    def logout(self):
        self.controller.set_auth_token(None)
        self.controller.show_frame(MainLoginSelector)

class ManagerDashboardFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        ttk.Label(self, text="Manager Dashboard",
                  font=("Arial", 20, "bold")).pack(pady=30)

        ttk.Button(self, text="View Orders",
                   command=lambda: controller.show_frame(OrdersFrame),
                   width=30).pack(pady=10)

        ttk.Button(self, text="Manage Books",
                   command=lambda: controller.show_frame(BookListFrame),
                   width=30).pack(pady=10)

        ttk.Button(self, text="Logout",
                   command=self.logout,
                   width=30).pack(pady=10)

    def logout(self):
        self.controller.set_auth_token(None)
        self.controller.show_frame(MainLoginSelector)

class OrderDetailsFrame(ttk.Frame):
    def __init__(self, parent, controller, order_id, items):
        super().__init__(parent)
        self.controller = controller
        self.order_id = order_id
        self.items = items
        
        # Title
        ttk.Label(self, text="Order Details", font=('Arial', 16, 'bold')).pack(pady=20)

        columns = ("ItemID", "Title", "OrderType", "Price")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')

        self.tree.heading('ItemID', text='Item ID')
        self.tree.heading('Title', text='Title')
        self.tree.heading('OrderType', text='Status')
        self.tree.heading('Price', text='Price')

        self.tree.column('ItemID', width=80)
        self.tree.column('Title', width=250)
        self.tree.column('OrderType', width=80)
        self.tree.column('Price', width=100)
        
        self.tree.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.load_items()
        
        # Form Block
        form_block = ttk.Frame(self, padding="20 20 20 20")
        form_block.pack(pady=50, padx=50)

        
        # buttons
        button_frame = ttk.Frame(form_block)
        button_frame.grid(row=0, column=0)
        ttk.Button(button_frame, text="mark as returned", command=self.mark_returned).pack(side='left', padx=10)
        ttk.Button(button_frame, text="back", command=lambda: controller.show_frame(OrdersFrame)).pack(side='left', padx=10)
        
    def load_items(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for item in self.items:
            self.tree.insert("", "end", values=(
                item.get('BookID'),
                item.get('Title'),
                item.get('OrderType'),
                item.get('Price')
            ))

    def mark_returned(self):
        selected = self.tree.selection()
        if not selected:
            return

        selected_item_values = self.tree.item(selected[0])["values"]
        
        book_id = selected_item_values[0]

        if not selected_item_values[2] == 'rent':
            return
        
        auth_header_value = self.controller.get_auth_token()
        if not auth_header_value:
            messagebox.showerror("Error", "User not logged in or token expired.")
            return

        headers = {
            'Authorization': f'Bearer {auth_header_value}',
            'Content-Type': 'application/json'
        }

        try:

            def task():
                return requests.put(
                    f"{API_BASE_URL}/orderitem/{book_id}", 
                    json={"ordertype": "returned"},
                    headers=headers
                )

            def done(response, error):
                if response.status_code == 200:
                    self.refreshapi()
                else:
                    # Handle API errors
                    error_message = response.json().get('message', 'Unknown API Error')
                    messagebox.showerror("Error", f"Failed to update status for Book ID {book_id}. Status: {response.status_code}. Message: {error_message}")
                    
            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")
        
    def refreshapi(self):
        auth_header_value = self.controller.get_auth_token()
        headers = {'Authorization': f'Bearer {auth_header_value}'}

        def task():
            return requests.get(f"{API_BASE_URL}/orderitems/{self.order_id}", headers=headers)

        def done(response, error):
            if error or response is None:
                messagebox.showerror("Error", "Failed to refresh items.")
                return

            if response.status_code == 200:
                self.items = response.json()
                self.load_items()
            else:
                messagebox.showerror("Error", f"Failed to reload. Status: {response.status_code}")

        self.controller.run_async(task, done)

class MyOrderDetailsFrame(ttk.Frame):
    def __init__(self, parent, controller, order_id, items):
        super().__init__(parent)
        self.controller = controller
        self.order_id = order_id
        self.items = items
        
        ttk.Label(self, text="Order Details", font=('Arial', 16, 'bold')).pack(pady=20)

        columns = ("BookID", "Title", "OrderType", "Price")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')

        self.tree.heading('BookID', text='Book ID')
        self.tree.heading('Title', text='Title')
        self.tree.heading('OrderType', text='Status')
        self.tree.heading('Price', text='Price')

        self.tree.column('BookID', width=80)
        self.tree.column('Title', width=250)
        self.tree.column('OrderType', width=80)
        self.tree.column('Price', width=100)
        
        self.tree.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.load_items()

        # buttons
        
        form_block = ttk.Frame(self, padding="20 20 20 20")
        form_block.pack(pady=50, padx=50)

        button_frame = ttk.Frame(form_block)
        button_frame.grid(row=0, column=0)
        ttk.Button(button_frame, text="Back", command=lambda: controller.show_frame(MyOrdersFrame)).pack(side='left', padx=10)
        
    def load_items(self):
        for item in self.items:
            self.tree.insert("", "end", values=(
                item.get('BookID'),
                item.get('Title'),
                item.get('OrderType'),
                item.get('Price')
            ))

class CustomerSearchFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="Book Inventory Search", font=("Arial", 20, "bold")).pack(pady=20)

        # buttons + search
        search_frame = ttk.Frame(self)
        search_frame.pack(pady=10)
        
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=50).pack(side=tk.LEFT, padx=10)
        ttk.Button(search_frame, text="search", command=self.search_books).pack(side=tk.LEFT)
        ttk.Button(search_frame, text="clear search", command=self.search_clear).pack(side=tk.LEFT)

        # --- Book List Treeview ---
        columns = ("BookID", "Title", "Author", "BuyPrice", "RentPrice", "Status", "Quantity")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')

        self.tree.heading('BookID', text='ID')
        self.tree.heading('Title', text='Title')
        self.tree.heading('Author', text='Author')
        self.tree.heading('BuyPrice', text='Buy Price')
        self.tree.heading('RentPrice', text='Rent Price')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Quantity', text='Inventory')

        self.tree.column('Quantity', width = 50)

        self.tree.column("BookID", width=0, stretch=False)
        self.tree.column('Status', width=0, stretch=False)
        self.tree.pack(fill='both', expand=True, padx=20, pady=10)
        
        # buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(pady=15)
        
        ttk.Button(action_frame, text="rating", command=self.rate).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="buy selected", command=self.buy).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="rent selected", command=self.rent).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="checkout", command=lambda: controller.show_frame(CheckoutFrame)).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="back", command=lambda: controller.show_frame(CustomerDashboardFrame)).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="logout", command=self.logout).pack(side=tk.LEFT, padx=10)
        
        # Load all books initially
        self.search_books() 

    def search_books(self):
        search_term = self.search_var.get().strip()
        
        # Clear existing entries
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            auth_header_value = self.controller.get_auth_token()
            if not auth_header_value:
                messagebox.showerror("Error", "Authentication token is missing.")
                return

            headers = {'Authorization': f'Bearer {auth_header_value}'}
            
            params = {}
            if search_term:
                params['query'] = search_term

            def task():
                return requests.get(f"{API_BASE_URL}/books", headers={'Authorization': f'Bearer {self.controller.get_auth_token()}'}, params=params)
            def done(response, error):
                if response.status_code == 200:
                    books = response.json()
                    
                    for book in books:
                        self.tree.insert("", "end", values=(
                            book['BookID'],
                            book['Name'],
                            book['Author'],
                            book['Buyprice'],
                            book['Rentprice'],
                            book['Status'],
                            book['Quantity']
                        ))
                else:
                    messagebox.showerror("API Error", f"Failed to fetch books. Status: {response.status_code}")
            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")
    
    def search_clear(self):
        self.search_var.set("")
        self.search_books()

    def logout(self):
        """Clears auth token and returns to the login screen."""
        self.controller.set_auth_token(None)
        self.controller.show_frame(MainLoginSelector)

    def getdata(self):
        selected = self.tree.selection()
        if not selected:
            return None
        
        # Values are retrieved as a tuple in the order of column definition
        values = self.tree.item(selected[0], 'values')
        
        # Map values back to a dictionary using the column names for easy access
        return {
            'BookID': values[0],
            'Title': values[1],
            'Author': values[2],
            'BuyPrice': values[3],
            'RentPrice': values[4],
            'Status': values[5]
        }
    
    def cart(self, transaction):
        book_data = self.getdata()
        
        if not book_data:
            return

        if self.controller.addcart(book_data, transaction):
            messagebox.showinfo("cart update", f"'{book_data['Title']}' added to cart for {transaction}")
        else:
            messagebox.showwarning("can't do that buddy", f"'{book_data['Title']}' is already in cart")

    def buy(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        book_data = self.tree.item(selected[0], 'values')

        if int(book_data[6]) < 1:
            messagebox.showwarning("out of stock", "I have no more")
            return

        self.cart('buy')
    
    def rent(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        book_data = self.tree.item(selected[0], 'values')

        if int(book_data[6]) < 1:
            messagebox.showwarning("out of stock", "bros tryna rent air")
            return

        self.cart('rent')
    
    def rate(self):
        selected = self.tree.selection()
        if not selected:
            return

        book_data = self.tree.item(selected[0])["values"]
        self.controller.show_frame(RateBookFrame, book_data=book_data)
    
class CheckoutFrame(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="Checkout", font=("Arial", 20, "bold")).pack(pady=20)

        # Treeview
        columns = ("BookID", "Title", "Type", "Price")
        self.tree = ttk.Treeview(self, columns=columns, show='headings')

        self.tree.heading('BookID', text='ID')
        self.tree.heading('Title', text='Title')
        self.tree.heading('Type', text='Transaction')
        self.tree.heading('Price', text='Price')
        
        self.tree.column("BookID", width=0, stretch=False)
        
        self.tree.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.total_cost_var = tk.StringVar(value="Total: $0.00")
        ttk.Label(self, textvariable=self.total_cost_var, font=('Arial', 14, 'bold')).pack(pady=10)

        # buttons
        action_frame = ttk.Frame(self)
        action_frame.pack(pady=15)
        
        ttk.Button(action_frame, text="Confirm Order", command=self.confirm_checkout).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="Clear Cart", command=self.clear_and_back).pack(side=tk.LEFT, padx=10)
        ttk.Button(action_frame, text="Back to Search", command=lambda: controller.show_frame(CustomerSearchFrame)).pack(side=tk.LEFT, padx=10)

        self.load_cart_items()

    def load_cart_items(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        items = self.controller.get_cart_items()
        total_cost = 0.0

        for item in items:
            total_cost += item['price']
            self.tree.insert("", "end", values=(
                item['book_id'],
                item['title'],
                item['type'].capitalize(),
                f"${item['price']:.2f}"
            ))
            
        self.total_cost_var.set(f"Total: ${total_cost:.2f}")

    def clear_and_back(self):
        self.controller.clear_cart()
        self.controller.show_frame(CustomerSearchFrame)

    def confirm_checkout(self):
        items = self.controller.get_cart_items()
        
        if not items:
            messagebox.showwarning("cart empty", "nothing in yor cart")
            return

        auth_header_value = self.controller.get_auth_token()
        user_id = self.controller.user_id

        if not auth_header_value or not user_id:
            messagebox.showerror("Login Required", "You must be logged in to place an order.")
            return

        payload = {
            "user_id": user_id, 
            "items": items
        }
        
        headers = {'Authorization': f'Bearer {auth_header_value}', 'Content-Type': 'application/json'}

        try:
            def task():
                return requests.post(f"{API_BASE_URL}/order", json=payload, headers=headers)
            def done(response, error):
                if response.status_code == 201:
                    result = response.json()

                    order_id = result.get('order_id')
                    total_cost = result.get('total_cost', 0.0)
                    
                    username = self.controller.username
                    user_email = self.controller.user_email

                    # file write
                    filename = f"order{order_id}.txt"
                    file_content = f"RE: order #{order_id}\n"
                    file_content += f"From: jasonlau@bookstore.com\n"
                    file_content += f"To: {user_email}\n\n"
                    file_content += f"Thank you, {username}, for ordering at our store. we hope you enjoy reading these books.\n\n"
                    file_content += f"here are the items you ordered:\n"
                    
                    #add items
                    for item in items:
                        file_content += f"  {item['title']} ({item['type'].capitalize()}) - ${item['price']:.2f}\n"
                    
                    file_content += f"\n"
                    file_content += f"The total cost of your order was ${total_cost:.2f}\n"

                    try:
                        # write the confirmation details to a local and send the email
                        with open(filename, "w") as file:
                            file.write(file_content)
                        
                        file_info = f"\nemail saved as '{filename}'"
                        self.sendemail(file_content)
                    except IOError as e:
                        file_info = f"\nCould not save receipt file: {e}"

                    self.controller.clear_cart()
                    # Return to search to see updated stock status
                    self.controller.show_frame(CustomerSearchFrame)
                else:
                    error_message = response.json().get('message', 'Unknown API Error')
                    messagebox.showerror("Checkout Failed", f"Status {response.status_code}: {error_message}")

            self.controller.run_async(task, done)

        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", f"Could not connect to the API server: {e}")
        
    def sendemail(self, email):
        # dummy email send function
        return

class RateBookFrame(ttk.Frame):
    def __init__(self, parent, controller, book_data=None):
        super().__init__(parent)
        self.controller = controller
        self.book_data = book_data

        if self.book_data:
            # Assuming book_data structure: (book_id, title, author, buy, rent, status)
            self.book_id, self.title, self.author, _, _, _, _ = self.book_data
        else:
            self.book_id = None
            self.title = "Unknown Book"
            self.author = "N/A"
            messagebox.showwarning("Data Error", "No book data provided. Cannot proceed.")
            return

        header_frame = ttk.Frame(self)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(header_frame, text=f"reviews for {self.title}", font=('Arial', 16, 'bold')).pack(side='left')
        
        ttk.Button(header_frame, text="back", command=lambda: controller.show_frame(CustomerSearchFrame)).pack(side='right', padx=5)


        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        # avg
        self.avg_label = ttk.Label(tree_frame, text="average rating: --", font=("Arial", 12, "bold"))
        self.avg_label.pack(anchor='w', pady=(0,5))

        # --- Treeview ---
        self.tree = ttk.Treeview(tree_frame, columns=("Rating", "Comments"), show="headings")
        self.tree.heading("Rating", text="Rating")
        self.tree.heading("Comments", text="Comment")

        self.tree.column("Rating", width=100, anchor='center')
        self.tree.column("Comments", width=450)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')



        self.load_ratings(self.book_id)

        ttk.Separator(self, orient='horizontal').pack(fill='x', padx=20, pady=10)

        self._setup_submission_form()

    def load_ratings(self, book_id):


        def task():
            return requests.get(f"{API_BASE_URL}/rating/{book_id}")

        def done(response, error):

            data = response.json()
            # clear rows
            for row in self.tree.get_children():
                self.tree.delete(row)

            total = 0
            count = 0

            # insert rows + compute average
            for entry in data:
                rating = entry.get("Rating")
                comment = entry.get("Comments", "")

                self.tree.insert("", "end", values=(rating, comment))

                if rating is not None:
                    total += rating
                    count += 1

            # update average
            if count > 0:
                avg = round(total / count, 2)
                self.avg_label.config(text=f"average rating: {avg}")
            else:
                self.avg_label.config(text="average rating: --")

        self.controller.run_async(task, done)

    def _setup_submission_form(self):
        form_frame = ttk.Frame(self)
        form_frame.pack(padx=20, pady=5, fill='x')

        ttk.Label(form_frame, text="write a review", font=("Arial", 14)).grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))

        
        ttk.Label(form_frame, text="Rating:", font=("Arial", 10)).grid(row=1, column=0, sticky='w', pady=5, padx=5)
        
        self.rating_value = tk.IntVar(value=3) 
        self.rating_scale = ttk.Scale(form_frame, 
                                      from_=1, to=5, 
                                      orient='horizontal', 
                                      variable=self.rating_value)
        self.rating_scale.grid(row=1, column=1, sticky='ew', padx=10)

        self.rating_label = ttk.Label(form_frame, text="3")
        self.rating_label.grid(row=1, column=2, sticky='w')
        
        scale_update = lambda e: self.rating_label.config(text=f"{self.rating_value.get()}")
        self.rating_scale.bind("<Motion>", scale_update)
        self.rating_scale.bind("<ButtonRelease-1>", scale_update)
        
        form_frame.grid_columnconfigure(1, weight=1)

        # comment input
        ttk.Label(form_frame, text="Comment:", font=("Arial", 10)).grid(row=2, column=0, sticky='nw', pady=5, padx=5)
        
        self.comments_text = tk.Text(form_frame, height=3, width=50, wrap='word')
        self.comments_text.grid(row=2, column=1, columnspan=2, sticky='ew', padx=10, pady=5)
        
        # submit
        ttk.Button(form_frame, 
                   text="submit review", 
                   command=self.submit_review,
                   style='Accent.TButton'
        ).grid(row=3, column=1)

    def submit_review(self):
        if not self.book_id:
            messagebox.showerror("Error", "Book ID is missing. Cannot submit review.")
            return

        rating = self.rating_value.get()
        comments = self.comments_text.get("1.0", "end-1c").strip()

        if rating < 1 or rating > 5:
            messagebox.showerror("Validation Error", "Rating must be between 1 and 5.")
            return

        try:
            auth_token = self.controller.get_auth_token()
        except:
            messagebox.showerror("Authentication Error", "Controller must implement get_auth_token().")
            return

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

        try:
            def task():
                return requests.post(
                    f"{API_BASE_URL}/rating",
                    json={
                        "book_id": self.book_id,
                        "customer_id": self.controller.user_id,
                        "rating": rating,
                        "comments": comments
                    },
                    headers=headers
                )
            def done(response, error):
                if response.status_code in (200, 201):
                    self.comments_text.delete("1.0", "end")
                    self.rating_value.set(3)
                    self.load_ratings(self.book_id)
                else:
                    messagebox.showerror("API Error", response.json().get("message", "Unknown error"))
            self.controller.run_async(task, done)
        except requests.exceptions.RequestException as e:
            messagebox.showerror("Network Error", str(e))


if __name__ == "__main__":
    app = BookstoreApp()
    app.mainloop()