from flask import Flask, request, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import create_tables, get_db_connection

app = Flask(__name__, static_folder="css")


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):
            return redirect(url_for("dashboard"))

        return "Invalid email or password!"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/create-user", methods=["GET", "POST"])
def create_user():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])
        role = request.form["role"]

        connection = get_db_connection()

        try:
            connection.execute(
                """
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, password, role)
            )
            connection.commit()
        except Exception:
            connection.close()
            return "User could not be created. Check whether the email already exists."

        connection.close()
        return redirect(url_for("manage_users"))

    return render_template("create_user.html")


@app.route("/manage-users")
def manage_users():
    connection = get_db_connection()
    users = connection.execute("SELECT * FROM users").fetchall()
    connection.close()

    return render_template("manage_user.html", users=users)


@app.route("/edit-user", methods=["GET", "POST"])
def edit_user():
    user_id = request.args.get("id")

    connection = get_db_connection()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if not user:
        connection.close()
        return "User not found!", 404

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        role = request.form["role"]
        status = request.form["status"]

        try:
            connection.execute(
                """
                UPDATE users
                SET name = ?, email = ?, role = ?, status = ?
                WHERE id = ?
                """,
                (name, email, role, status, user_id)
            )
            connection.commit()
        except Exception:
            connection.close()
            return "User could not be updated. Check whether the email already exists."

        connection.close()
        return redirect(url_for("manage_users"))

    connection.close()
    return render_template("edit_user.html", user=user)


@app.route("/create-task", methods=["GET", "POST"])
def create_task():
    connection = get_db_connection()

    users = connection.execute(
        "SELECT id, name, email FROM users WHERE role = 'Team Member' AND status = 'Active'"
    ).fetchall()

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form.get("description", "").strip()
        assigned_to = request.form.get("assigned_to")
        priority = request.form["priority"]
        deadline = request.form.get("deadline") or None

        if not title:
            connection.close()
            return "Task title is required!", 400

        if not assigned_to:
            connection.close()
            return "Please select a team member!", 400

        valid_user = connection.execute(
            "SELECT id FROM users WHERE id = ? AND role = 'Team Member' AND status = 'Active'",
            (assigned_to,)
        ).fetchone()

        if not valid_user:
            connection.close()
            return "Please select a valid active team member!", 400

        connection.execute(
            """
            INSERT INTO tasks (title, description, assigned_to, priority, deadline)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, description, assigned_to, priority, deadline)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("manage_tasks"))

    connection.close()
    return render_template("create_task.html", users=users)


@app.route("/manage-task")
def manage_tasks():
    connection = get_db_connection()

    tasks = connection.execute(
        """
        SELECT tasks.*, users.name AS assigned_name
        FROM tasks
        LEFT JOIN users ON tasks.assigned_to = users.id
        ORDER BY tasks.id DESC
        """
    ).fetchall()

    connection.close()

    return render_template("manage_tasks.html", tasks=tasks)


@app.route("/edit-task", methods=["GET", "POST"])
def edit_task():
    task_id = request.args.get("id")

    connection = get_db_connection()

    task = connection.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    if not task:
        connection.close()
        return "Task not found!", 404

    users = connection.execute(
        "SELECT id, name FROM users WHERE role = 'Team Member' AND status = 'Active'"
    ).fetchall()

    if request.method == "POST":
        title = request.form["title"].strip()
        description = request.form.get("description", "").strip()
        assigned_to = request.form.get("assigned_to")
        priority = request.form["priority"]
        status = request.form["status"]
        deadline = request.form.get("deadline") or None

        if not title or not assigned_to:
            connection.close()
            return "Task title and team member are required!", 400

        connection.execute(
            """
            UPDATE tasks
            SET title = ?, description = ?, assigned_to = ?,
                priority = ?, status = ?, deadline = ?
            WHERE id = ?
            """,
            (title, description, assigned_to, priority, status, deadline, task_id)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("manage_tasks"))

    connection.close()

    return render_template(
        "edit_task.html",
        task=task,
        users=users
    )


@app.route("/my-tasks")
def my_tasks():
    return render_template("my_tasks.html")


@app.route("/task-details")
def task_details():
    return render_template("task_details.html")


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)