from flask import Flask
from database import create_tables

app = Flask(__name__)


@app.route("/")
def home():
    return "Task Management System is running!"


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)