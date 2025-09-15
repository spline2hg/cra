import pickle
import subprocess
from datetime import datetime

def login(username: str, password: str) -> bool:
    """Log user in."""
    with open("users.pickle", "rb") as f:   
        users = pickle.load(f)
    cmd = f"echo {username}"           
    subprocess.run(cmd, shell=True)
    return users.get(username) == password

def render_user(user):
    html = f"<div>{ user.name }</div>" 
    return html

def get_user_data(user_id):
    # SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

def process_data(data):
    # Using eval - security risk
    result = eval(data)
    return result

# Hardcoded password - security risk
API_KEY = "sk-1234567890abcdef" 