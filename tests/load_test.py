from locust import HttpUser, task, between
import random

class StudentApiUser(HttpUser):
    wait_time = between(1, 2)
    last_student_ids = []

    @task(1)
    def home(self):
        self.client.get("/")

    @task(1)
    def health(self):
        self.client.get("/health")

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
        response = self.client.post("/students", json=payload)
        if response.status_code == 201:
            # store created ID for subsequent GET/PUT/DELETE
            self.last_student_ids.append(response.json()["id"])

    @task(1)
    def get_student_by_id(self):
        if self.last_student_ids:
            student_id = random.choice(self.last_student_ids)
            self.client.get(f"/students/{student_id}")

    @task(1)
    def update_student(self):
        if self.last_student_ids:
            student_id = random.choice(self.last_student_ids)
            payload = {"gpa": round(random.uniform(6.0, 10.0), 2)}
            self.client.put(f"/students/{student_id}", json=payload)

    @task(1)
    def delete_student(self):
        if self.last_student_ids:
            student_id = self.last_student_ids.pop(0)  # remove from list after deletion
            self.client.delete(f"/students/{student_id}")

