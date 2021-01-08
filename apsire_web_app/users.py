from werkzeug.security import generate_password_hash

users = {
    "hello": generate_password_hash("world"),
    "test": generate_password_hash("123")
}