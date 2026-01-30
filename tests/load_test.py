# load_test.py
from locust import HttpUser, task, between
import random

class StudentApiUser(HttpUser):
    wait_time = between(1, 2)

    @task(2)
    def get_students(self):
        self.client.get("/students")

    @task(1)
    def create_student(self):
        student_id = random.randint(1000, 9999)
        payload = {
            "name": f"Test User {student_id}",
            "domain": "Engineering",
            "gpa": round(random.uniform(6.0, 10.0), 2),
            "email": f"testuser{student_id}@example.com"
        }
        self.client.post("/students", json=payload) 

