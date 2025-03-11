"""
Route handlers and view functions.
"""

from flask import render_template, jsonify, redirect, request, session, url_for, flash
import requests
import config
from models import login_required, teacher_required, User, Teacher, Student

def init_routes(app):
    """Initialize all routes for the Flask app."""
    
    @app.route('/')
    def index():
        """Main app index showing links to all sub-apps."""
        user_id = session.get('user_id')
        user_type = session.get('user_type')
        
        # If teacher is logged in, redirect to dashboard
        if user_id and user_type == 'teacher':
            return redirect(url_for('dashboard'))
        
        return render_template('index.html', 
                            kinesthetic_url=f"http://localhost:{config.KINESTHETIC_APP_PORT}",
                            readwrite_url=f"http://localhost:{config.READWRITE_APP_PORT}",
                            visual_url=f"http://localhost:{config.VISUAL_APP_PORT}",
                            user_id=user_id,
                            user_type=user_type)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handle user login."""
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            user_type = request.form.get('user_type')
            
            if not email or not password or not user_type:
                flash('Please fill in all fields')
                return render_template('login.html')
            
            try:
                # Verify with Firebase Authentication
                user = User.get_by_email(email)
                
                # Store user info in session
                session['user_id'] = user.uid
                session['email'] = user.email
                session['user_type'] = user_type
                
                # If user is a teacher, fetch profile from Firestore
                if user_type == 'teacher':
                    # Check if the user exists in Firestore
                    teacher = Teacher.get(user.uid)
                    
                    if not teacher:
                        # First time login after registration - store basic info
                        Teacher.create_basic(user.uid, user.email)
                    
                    return redirect(url_for('dashboard'))
                else:
                    # Student login - redirect to index
                    return redirect(url_for('index'))
                    
            except Exception as e:
                flash(f'Login failed: {str(e)}')
                return render_template('login.html')
        
        return render_template('login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """Handle teacher registration."""
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            name = request.form.get('name')
            school = request.form.get('school')
            
            if not email or not password or not confirm_password or not name or not school:
                flash('Please fill in all fields')
                return render_template('register.html')
                
            if password != confirm_password:
                flash('Passwords do not match')
                return render_template('register.html')
            
            try:
                # Create user in Firebase Authentication
                user = User.create_user(email, password)
                
                # Store additional teacher data in Firestore
                Teacher.create(user.uid, name, email, school)
                
                flash('Registration successful! Please login.')
                return redirect(url_for('login'))
                
            except Exception as e:
                flash(f'Registration failed: {str(e)}')
                return render_template('register.html')
        
        return render_template('register.html')

    @app.route('/dashboard')
    @teacher_required
    def dashboard():
        """Teacher dashboard."""
        user_id = session.get('user_id')
        
        # Get teacher data from Firestore
        teacher_data = Teacher.get(user_id)
        
        # Get all students for this teacher
        students = Student.get_all_for_teacher(user_id)
        
        return render_template('dashboard.html', 
                            teacher=teacher_data,
                            students=students,
                            kinesthetic_url=f"http://localhost:{config.KINESTHETIC_APP_PORT}",
                            readwrite_url=f"http://localhost:{config.READWRITE_APP_PORT}",
                            visual_url=f"http://localhost:{config.VISUAL_APP_PORT}")

    @app.route('/add_student', methods=['POST'])
    @teacher_required
    def add_student():
        """Add a new student for the teacher."""
        user_id = session.get('user_id')
        
        name = request.form.get('student_name')
        email = request.form.get('student_email')
        password = request.form.get('student_password')
        
        if not name or not email or not password:
            flash('Please fill in all student details')
            return redirect(url_for('dashboard'))
        
        try:
            # Create the student
            Student.create(user_id, name, email, password)
            flash(f'Student {name} has been added successfully')
        except Exception as e:
            flash(f'Failed to add student: {str(e)}')
        
        return redirect(url_for('dashboard'))

    @app.route('/edit_student/<student_id>', methods=['GET', 'POST'])
    @teacher_required
    def edit_student(student_id):
        """Edit a student's details."""
        user_id = session.get('user_id')
        
        # Get student data
        student = Student.get(student_id)
        
        # Check if the student belongs to this teacher
        if not student or student.get('teacher_id') != user_id:
            if request.method == 'POST':
                return jsonify({'error': 'Permission denied'}), 403
            else:
                flash('You do not have permission to edit this student')
                return redirect(url_for('dashboard'))
        
        if request.method == 'POST':
            name = request.form.get('student_name')
            email = request.form.get('student_email')
            
            try:
                Student.update(student_id, name=name, email=email)
                
                # If it's an AJAX request, return a JSON response
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': f'Student {name} has been updated successfully'})
                
                flash(f'Student {name} has been updated successfully')
                return redirect(url_for('dashboard'))
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': str(e)}), 500
                    
                flash(f'Failed to update student: {str(e)}')
                return redirect(url_for('dashboard'))
        
        # GET request is not needed anymore since we're using a modal
        # Just redirect to dashboard if someone tries to access this URL directly
        return redirect(url_for('dashboard'))

    @app.route('/delete_student/<student_id>')
    @teacher_required
    def delete_student(student_id):
        """Delete a student."""
        user_id = session.get('user_id')
        
        # Get student data
        student = Student.get(student_id)
        
        # Check if the student belongs to this teacher
        if not student or student.get('teacher_id') != user_id:
            flash('You do not have permission to delete this student')
            return redirect(url_for('dashboard'))
        
        try:
            Student.delete(student_id)
            flash('Student has been deleted successfully')
        except Exception as e:
            flash(f'Failed to delete student: {str(e)}')
        
        return redirect(url_for('dashboard'))

    @app.route('/logout')
    def logout():
        """Log out the user."""
        session.pop('user_id', None)
        session.pop('email', None)
        session.pop('user_type', None)
        flash('You have been logged out')
        return redirect(url_for('index'))

    @app.route('/kinesthetic')
    def kinesthetic_redirect():
        """Redirect to the kinesthetic app."""
        return redirect(f"http://localhost:{config.KINESTHETIC_APP_PORT}")

    @app.route('/readwrite')
    def readwrite_redirect():
        """Redirect to the readwrite app."""
        return redirect(f"http://localhost:{config.READWRITE_APP_PORT}")

    @app.route('/visual')
    def visual_redirect():
        """Redirect to the visual app."""
        return redirect(f"http://localhost:{config.VISUAL_APP_PORT}")

    @app.route('/api/status')
    def api_status():
        """API endpoint to check the status of all apps."""
        status = {
            'main': 'running',
            'kinesthetic': 'unknown',
            'readwrite': 'unknown',
            'visual': 'unknown'
        }
        
        # Check kinesthetic app
        try:
            response = requests.get(f"http://localhost:{config.KINESTHETIC_APP_PORT}/api/info")
            if response.status_code == 200:
                status['kinesthetic'] = 'running'
        except:
            status['kinesthetic'] = 'not running'
        
        # Check readwrite app
        try:
            response = requests.get(f"http://localhost:{config.READWRITE_APP_PORT}/api/info")
            if response.status_code == 200:
                status['readwrite'] = 'running'
        except:
            status['readwrite'] = 'not running'
        
        # Check visual app
        try:
            response = requests.get(f"http://localhost:{config.VISUAL_APP_PORT}/api/info")
            if response.status_code == 200:
                status['visual'] = 'running'
        except:
            status['visual'] = 'not running'
        
        return jsonify(status)
