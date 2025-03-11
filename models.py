"""
Data models and Firebase integration.
"""

import firebase_admin
from firebase_admin import credentials, auth, firestore
from functools import wraps
from flask import session, redirect, url_for, request, flash

# Initialize Firebase
cred = credentials.Certificate("research-app-9fff9-firebase-adminsdk-fbsvc-35cdf97b1e.json")
firebase_app = firebase_admin.initialize_app(cred)
db = firestore.client()

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def teacher_required(f):
    """Decorator to require teacher role for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'teacher':
            flash('You need to be logged in as a teacher to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class User:
    @staticmethod
    def get_by_email(email):
        """Get a user by email from Firebase Auth."""
        return auth.get_user_by_email(email)
    
    @staticmethod
    def create_user(email, password):
        """Create a new user in Firebase Auth."""
        return auth.create_user(email=email, password=password)

class Teacher:
    @staticmethod
    def get(user_id):
        """Get teacher data from Firestore."""
        teacher_ref = db.collection('teachers').document(user_id)
        return teacher_ref.get().to_dict()
    
    @staticmethod
    def create(user_id, name, email, school):
        """Create a new teacher record in Firestore."""
        db.collection('teachers').document(user_id).set({
            'name': name,
            'email': email,
            'school': school,
            'created_at': firestore.SERVER_TIMESTAMP
        })
    
    @staticmethod
    def create_basic(user_id, email):
        """Create a basic teacher record with just email."""
        db.collection('teachers').document(user_id).set({
            'email': email,
            'created_at': firestore.SERVER_TIMESTAMP
        })

class Student:
    @staticmethod
    def get_all_for_teacher(teacher_id):
        """Get all students for a specific teacher."""
        students_ref = db.collection('students').where('teacher_id', '==', teacher_id)
        students = []
        
        for doc in students_ref.stream():
            student_data = doc.to_dict()
            student_data['id'] = doc.id
            students.append(student_data)
            
        return students
    
    @staticmethod
    def get(student_id):
        """Get a student by ID."""
        student_ref = db.collection('students').document(student_id)
        student = student_ref.get()
        if not student.exists:
            return None
        student_data = student.to_dict()
        student_data['id'] = student.id
        return student_data
    
    @staticmethod
    def create(teacher_id, name, email, password):
        """Create a new student under a teacher."""
        try:
            # Create user in Firebase Auth
            user = User.create_user(email, password)
            
            # Store student data in Firestore
            student_ref = db.collection('students').document(user.uid)
            student_ref.set({
                'name': name,
                'email': email,
                'teacher_id': teacher_id,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            return user.uid
        except Exception as e:
            raise Exception(f"Failed to create student: {str(e)}")
    
    @staticmethod
    def update(student_id, name=None, email=None):
        """Update a student's information."""
        update_data = {}
        
        if name:
            update_data['name'] = name
        
        if email:
            update_data['email'] = email
        
        if update_data:
            db.collection('students').document(student_id).update(update_data)
    
    @staticmethod
    def delete(student_id):
        """Delete a student."""
        try:
            # Delete from Firestore
            db.collection('students').document(student_id).delete()
            
            # Delete from Firebase Auth
            auth.delete_user(student_id)
            
            return True
        except Exception as e:
            raise Exception(f"Failed to delete student: {str(e)}")
