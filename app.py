from flask import Flask, request, render_template
from werkzeug.security import generate_password_hash
from database import create_tables, get_db_connection

app = Flask(__name__, static_folder="css")


@app.route("/")
def home():
    return render_template("manage.html")


@app.route("/create-user", methods=["GET", "POST"])
def create_user():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if user:
            connection.close()
            return "Email already exists!"

        password = generate_password_hash(password)

        connection.execute(
            """
            INSERT INTO users (name, email, password, role)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, password, role)
        )

        connection.commit()
        connection.close()

        return "User created successfully!"

    return render_template("create_user.html")


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)