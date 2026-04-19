from app import create_app, db
from app.models import Student
import random

def seed_students(count=100):
    domains = [
        "Electronics",
        "Mechanical",
        "Civil",
        "Computer Science",
        "Mathematics",
        "Physics"
    ]

    students = []
    for i in range(1, count + 1):
        students.append(
            Student(
                name=f"Student {i}",
                domain=random.choice(domains),
                gpa=round(random.uniform(5.0, 10.0), 2),
                email=f"student{i:03d}@university.edu"
            )
        )

    db.session.bulk_save_objects(students)
    db.session.commit()
    print(f" {count} students inserted successfully")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        seed_students(100)

