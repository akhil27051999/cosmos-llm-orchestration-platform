from flask import Blueprint, request, jsonify
from app.models import db, Student

student_bp = Blueprint('student', __name__)
    
@student_bp.route('', methods=['POST'])
def add_student():
    data = request.get_json()
    if not data or not all(key in data for key in ('name', 'domain', 'gpa', 'email')):
        return jsonify({"error": "Missing data"}), 400
        # Validate required fields
    
    # Create a new student instance

    new_student = Student(
        name=data['name'],
        domain=data['domain'],
        gpa=data['gpa'],
        email=data['email']
    )
    
    db.session.add(new_student)
    db.session.commit()
    
    return jsonify({"message": "Student added successfully!", "id": new_student.id}), 201

@student_bp.route('', methods=['GET'])
def get_students():
    students = Student.query.all()
    student_list = [
        {
            "id": student.id,
            "name": student.name,
            "domain": student.domain,
            "gpa": student.gpa,
            "email": student.email
        } for student in students
    ]
    
    return jsonify(student_list), 200

@student_bp.route('<int:student_id>', methods=['GET'])    
def get_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    return jsonify({
        "id": student.id,
        "name": student.name,
        "domain": student.domain,
        "gpa": student.gpa,
        "email": student.email
    }), 200

@student_bp.route('<int:student_id>', methods=['PUT'])
def update_student(student_id):
    student = Student.query.get_or_404(student_id)
    data = request.get_json()
    
    if not data or not any(key in data for key in ('name', 'domain', 'gpa', 'email')):
        return jsonify({"error": "No valid fields provided"}), 400

    if 'name' in data:
        student.name = data['name']
    if 'domain' in data:
        student.domain = data['domain']
    if 'gpa' in data:
        student.gpa = data['gpa']
    if 'email' in data:
        student.email = data['email']
    
    db.session.commit()
    
    return jsonify({"message": "Student updated successfully!"}), 200

@student_bp.route('<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    
    db.session.delete(student)
    db.session.commit()
    
    return jsonify({"message": "Student deleted successfully!"}), 200   
