import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import json # Import json for passing data to JS
from pytz import timezone
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


def current_time_ist():
    ist = timezone('Asia/Kolkata')
    return datetime.now(ist)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=True)  # New field for notice category
    timestamp = db.Column(db.DateTime, default=current_time_ist)
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
    # Fetch notices from the database
    notices_db = Notice.query.order_by(Notice.timestamp.desc()).all()
    
    # Prepare notices data for JavaScript, including placeholder images
    notices_data = []
    # Placeholder images for the public view, matching the original front-end's style
    # These should ideally be managed more robustly (e.g., stored in DB or linked to actual uploads)

    for notice in notices_db:
        image_url = None
        if notice.files:
            first_file = notice.files.split(",")[0]
            if first_file.lower().endswith(("png", "jpg", "jpeg")):
                image_url = url_for("uploaded_file", filename=first_file)
        notices_data.append({
            'id': notice.id,
            'title': notice.title,
            'content': notice.content[:100] + "..." if len(notice.content) > 100 else notice.content,  # short preview
            'category': notice.category if notice.category else 'announcements',
            'date': notice.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'image': image_url or url_for("static", filename="images/default.png")  # fallback
        })
    
    # Pass the JSON string of notices to the template
    return render_template("index.html", notices_json=notices_data)

@app.route("/notice/<int:id>")
def view_notice(id):
    notice = Notice.query.get_or_404(id)
    files = notice.files.split(",") if notice.files else []
    file_urls = [url_for("uploaded_file", filename=f) for f in files]
    return render_template("view_notice.html", notice=notice, file_urls=file_urls)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session["user_id"] = user.id
            flash("Logged in successfully!", "success")
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
        flash("Please log in to access the dashboard.", "warning")
        return redirect(url_for("login"))
    notices = Notice.query.order_by(Notice.timestamp.desc()).all()
    return render_template("dashboard.html", notices=notices)


@app.route("/add", methods=["GET", "POST"])
def add_notice():
    if "user_id" not in session:
        # If the request is from the public index.html modal, it will be a POST.
        # If not logged in, it will redirect to login.
        flash("Please log in to add a notice.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form.get("category", "announcements") # Get category from form, default if not provided

        filenames = []
        # Check if files are sent (this will typically only happen from the admin add_notice.html)
        if "files" in request.files:
            files = request.files.getlist("files")
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(filepath)
                    filenames.append(filename)

        new_notice = Notice(title=title, content=content, category=category, files=",".join(filenames))
        db.session.add(new_notice)
        db.session.commit()
        flash("Notice added successfully!", "success")
        
        # Redirect to admin dashboard after adding a notice
        return redirect(url_for("admin_dashboard"))

    # For GET requests, render the admin add_notice.html
    return render_template("add_notice.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_notice(id):
    if "user_id" not in session:
        flash("Please log in to edit notices.", "warning")
        return redirect(url_for("login"))

    notice = Notice.query.get_or_404(id)

    if request.method == "POST":
        notice.title = request.form["title"]
        notice.content = request.form["content"]
        notice.category = request.form.get("category", "announcements") # Update category

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
        flash("Please log in to delete notices.", "warning")
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
    # Add sample notices with categories if the database is empty
    if not Notice.query.first():
        db.session.add(Notice(title="Mid-term Exams Schedule", content="Mid-term examinations for all semesters will begin on 15th March 2024. Please check your registered courses for specific dates and times.", category="exams"))
        db.session.add(Notice(title="Annual Cultural Fest 2024", content="Join us for an exciting cultural celebration featuring performances, competitions, and food stalls. Participation certificates for all!", category="events"))
        db.session.add(Notice(title="Library Hours Extension", content="During exam weeks, the central library will remain open 24 hours. Study groups are encouraged, and quiet zones are available.", category="announcements"))
        db.session.add(Notice(title="Guest Lecture Series", content="Renowned industry experts will be delivering lectures on emerging technologies every Friday at 2 PM in the auditorium.", category="events"))
        db.session.add(Notice(title="Scholarship Opportunities", content="Undergraduate students are eligible for various merit-based scholarships. Applications are open until 30th March 2024.", category="announcements"))
        db.session.add(Notice(title="Campus Recruitment Drive", content="Top MNCs will be conducting placement drives next month. Resume workshops are mandatory for participating students.", category="events"))
        db.session.commit()


# ----------------------------
# Run App
# ----------------------------
if __name__ == "__main__":
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
