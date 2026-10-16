from flask import Flask, request, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import create_tables, get_db_connection

app = Flask(__name__, static_folder="css")
app.secret_key = "task-management-secret-key-change-later"


@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]

        connection = get_db_connection()

        user = connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if user and check_password_hash(user["password"], password):

            if user["status"] != "Active":
                return "Your account is inactive. Please contact the administrator."

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            if user["role"] in ["Admin", "Manager"]:
                return redirect(url_for("dashboard"))

            elif user["role"] == "Team Member":
                return redirect(
                    url_for("my_tasks", user_id=user["id"])
                )

            session.clear()
            return "Invalid user role!"

        return "Invalid email or password!"

    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("home"))

    if session.get("user_role") not in ["Admin", "Manager"]:
        return "Access Denied!", 403

    connection = get_db_connection()

    total_users = connection.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    total_tasks = connection.execute(
        "SELECT COUNT(*) FROM tasks"
    ).fetchone()[0]

    pending_tasks = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'Pending'"
    ).fetchone()[0]

    in_progress_tasks = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'In Progress'"
    ).fetchone()[0]

    completed_tasks = connection.execute(
        "SELECT COUNT(*) FROM tasks WHERE status = 'Completed'"
    ).fetchone()[0]

    overdue_tasks = connection.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE deadline < DATE('now', 'localtime')
        AND status != 'Completed'
    """).fetchone()[0]

    recent_tasks = connection.execute("""
        SELECT tasks.*, users.name AS assigned_name
        FROM tasks
        LEFT JOIN users ON tasks.assigned_to = users.id
        ORDER BY tasks.id DESC
        LIMIT 5
    """).fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        total_users=total_users,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        in_progress_tasks=in_progress_tasks,
        completed_tasks=completed_tasks,
        overdue_tasks=overdue_tasks,
        recent_tasks=recent_tasks
    )


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


@app.route("/manage-tasks")
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

@app.route("/delete-task", methods=["POST"])
def delete_task():
    task_id = request.form.get("task_id")

    connection = get_db_connection()

    task = connection.execute(
        "SELECT id FROM tasks WHERE id = ?",
        (task_id,)
    ).fetchone()

    if not task:
        connection.close()
        return "Task not found!", 404

    connection.execute(
        "DELETE FROM tasks WHERE id = ?",
        (task_id,)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("manage_tasks"))


@app.route("/my-tasks")
def my_tasks():
    user_id = request.args.get("user_id")

    if not user_id:
        return "Please provide a team member ID. Example: /my-tasks?user_id=1"

    connection = get_db_connection()

    user = connection.execute(
        "SELECT id, name FROM users WHERE id = ? AND role = 'Team Member'",
        (user_id,)
    ).fetchone()

    if not user:
        connection.close()
        return "Team member not found!", 404

    tasks = connection.execute(
        """
        SELECT *
        FROM tasks
        WHERE assigned_to = ?
        ORDER BY id DESC
        """,
        (user_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "my_tasks.html",
        tasks=tasks,
        user=user
    )


@app.route("/task-details")
def task_details():
    task_id = request.args.get("id")

    connection = get_db_connection()

    task = connection.execute(
        """
        SELECT tasks.*, users.name AS assigned_name, users.email AS assigned_email
        FROM tasks
        LEFT JOIN users ON tasks.assigned_to = users.id
        WHERE tasks.id = ?
        """,
        (task_id,)
    ).fetchone()

    connection.close()

    if not task:
        return "Task not found!", 404

    return render_template("task_details.html", task=task)
@app.route("/update-task-status", methods=["POST"])
def update_task_status():
    task_id = request.form.get("task_id")
    user_id = request.form.get("user_id")
    status = request.form.get("status")

    allowed_statuses = ["Pending", "In Progress", "Completed"]

    if status not in allowed_statuses:
        return "Invalid task status!", 400

    connection = get_db_connection()

    task = connection.execute(
        "SELECT id FROM tasks WHERE id = ? AND assigned_to = ?",
        (task_id, user_id)
    ).fetchone()

    if not task:
        connection.close()
        return "Task not found or not assigned to this user!", 404

    connection.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (status, task_id)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("my_tasks", user_id=user_id))
@app.route("/add-comment", methods=["POST"])
def add_comment():
    task_id = request.form.get("task_id")
    user_id = request.form.get("user_id")
    comment = request.form.get("comment", "").strip()

    if not comment:
        return "Comment cannot be empty!", 400

    connection = get_db_connection()

    task = connection.execute(
        "SELECT id FROM tasks WHERE id = ? AND assigned_to = ?",
        (task_id, user_id)
    ).fetchone()

    if not task:
        connection.close()
        return "Task not found!", 404

    connection.execute(
        """
        INSERT INTO task_comments (task_id, user_id, comment)
        VALUES (?, ?, ?)
        """,
        (task_id, user_id, comment)
    )

    connection.commit()
    connection.close()

    return redirect(url_for("task_comments", task_id=task_id, user_id=user_id))


@app.route("/task-comments")
def task_comments():
    task_id = request.args.get("task_id")
    user_id = request.args.get("user_id")

    connection = get_db_connection()

    task = connection.execute(
        "SELECT * FROM tasks WHERE id = ? AND assigned_to = ?",
        (task_id, user_id)
    ).fetchone()

    if not task:
        connection.close()
        return "Task not found!", 404

    comments = connection.execute(
        """
        SELECT task_comments.*, users.name AS user_name
        FROM task_comments
        JOIN users ON task_comments.user_id = users.id
        WHERE task_comments.task_id = ?
        ORDER BY task_comments.id DESC
        """,
        (task_id,)
    ).fetchall()

    connection.close()

    return render_template(
        "task_comments.html",
        task=task,
        comments=comments,
        user_id=user_id
    )
@app.route("/overdue-tasks")
def overdue_tasks():
    connection = get_db_connection()

    tasks = connection.execute("""
        SELECT tasks.*, users.name AS assigned_name
        FROM tasks
        LEFT JOIN users ON tasks.assigned_to = users.id
        WHERE tasks.deadline < DATE('now', 'localtime')
        AND tasks.status != 'Completed'
        ORDER BY tasks.deadline ASC
    """).fetchall()

    connection.close()

    return render_template("overdue_tasks.html", tasks=tasks)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))



if __name__ == "__main__":
    create_tables()
    app.run(debug=True)