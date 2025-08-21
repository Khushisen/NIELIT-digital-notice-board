import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# ----------------------------
# Flask Config
# ----------------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///noticeboard.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# File upload settings
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# ----------------------------
# Models
# ----------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    files = db.Column(db.String(500))  # Comma-separated filenames


# ----------------------------
# Helpers
# ----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


# ----------------------------
# Routes
# ----------------------------
@app.route("/")
def index():
    notices = Notice.query.order_by(Notice.timestamp.desc()).all()
    return render_template("index.html", notices=notices)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    notices = Notice.query.order_by(Notice.timestamp.desc()).all()
    return render_template("dashboard.html", notices=notices)


@app.route("/add", methods=["GET", "POST"])
def add_notice():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        filenames = []
        if "files" in request.files:
            files = request.files.getlist("files")
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(filepath)
                    filenames.append(filename)

        new_notice = Notice(title=title, content=content, files=",".join(filenames))
        db.session.add(new_notice)
        db.session.commit()
        flash("Notice added successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("add_notice.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_notice(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    notice = Notice.query.get_or_404(id)

    if request.method == "POST":
        notice.title = request.form["title"]
        notice.content = request.form["content"]

        if "files" in request.files:
            files = request.files.getlist("files")
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(filepath)
                    # append new files
                    if notice.files:
                        notice.files += "," + filename
                    else:
                        notice.files = filename

        db.session.commit()
        flash("Notice updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("edit_notice.html", notice=notice)


@app.route("/delete/<int:id>", methods=["POST"])
def delete_notice(id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    notice = Notice.query.get_or_404(id)
    db.session.delete(notice)
    db.session.commit()
    flash("Notice deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))


# ----------------------------
# Initialize Database
# ----------------------------
@app.before_request
def create_tables():
    db.create_all()
    # Create default admin if not exists
    if not User.query.filter_by(username="admin").first():
        hashed_pw = generate_password_hash("admin", method="pbkdf2:sha256")
        db.session.add(User(username="admin", password=hashed_pw))
        db.session.commit()


# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)

