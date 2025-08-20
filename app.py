import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///notices.db"
app.config["UPLOAD_FOLDER"] = "uploads"
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# ------------------ MODELS ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=True)
    filenames = db.Column(db.Text, nullable=True)  # multiple filenames, separated by ;
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------ ROUTES ------------------
@app.route("/")
def index():
    notices = Notice.query.order_by(Notice.timestamp.desc()).all()
    return render_template("index.html", notices=notices)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# -------- AUTH --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# -------- ADMIN DASHBOARD --------
@app.route("/dashboard")
@login_required
def dashboard():
    notices = Notice.query.order_by(Notice.timestamp.desc()).all()
    return render_template("dashboard.html", notices=notices)

# -------- ADD NOTICE (Admin only) --------
@app.route("/add", methods=["GET", "POST"])
@login_required
def add_notice():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        files = request.files.getlist("files")
        filenames = []
        for file in files:
            if file.filename != "":
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                file.save(filepath)
                filenames.append(file.filename)

        new_notice = Notice(title=title, content=content, filenames=";".join(filenames))
        db.session.add(new_notice)
        db.session.commit()
        return redirect(url_for("dashboard"))

    return render_template("add.html")

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_notice(id):
    notice = Notice.query.get_or_404(id)
    if request.method == "POST":
        notice.title = request.form["title"]
        notice.content = request.form["content"]

        files = request.files.getlist("files")
        filenames = []
        for file in files:
            if file.filename != "":
                filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                file.save(filepath)
                filenames.append(file.filename)

        if filenames:
            notice.filenames = ";".join(filenames)

        db.session.commit()
        return redirect(url_for("dashboard"))
    return render_template("edit.html", notice=notice)

@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete_notice(id):
    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    return redirect(url_for("dashboard"))


if __name__=="__main__":
    app.run(debug=True)