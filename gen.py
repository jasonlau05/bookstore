from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

bcrypt.check_password_hash(
    "$2b$12$p4hMGKZ.YuzAyX73DgqbP.9rISmVz3ljkNSuZFRmJGCuzRBPp/bIu",
    "password"
)