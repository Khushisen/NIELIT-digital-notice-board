from app import app, db, User
from werkzeug.security import generate_password_hash

def create_admin(username, password):
    with app.app_context():
        db.create_all()
        # Check if the user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"User '{username}' already exists!")
            return

        # Create new admin
        admin = User(username=username, password=generate_password_hash(password))
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully.")

if __name__ == "__main__":
    # Change credentials here if needed
    create_admin("admin", "admin123")
