from flask import Blueprint, render_template, request, jsonify
# from models import User
from werkzeug.security import generate_password_hash, check_password_hash

# Create a blueprint for authentication-related routes
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Process login logic here
        return jsonify({'message': 'Logged in successfully'})
    return render_template('login.html')

@auth_bp.route('/register', methods=['POST'])
def register():
    # Process registration logic here
    return jsonify({'message': 'User registered successfully'})



from flask import Flask, jsonify, request, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Enable cross-origin request from the iOS app

# Configure database connection
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Import models (must be after db initialization to avoid circular imports
from models import Task

# CLI command to initialize the database
@app.cli.command('initdb')
def initdb_command():
    db.create_all()
    print('Initialized the database.')

# API Endpoints

# Get all tasks
@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([
        {'id': task.id,
         'title': task.title,
         'description': task.description,
         'status': task.status
         } for task in tasks])

    # Get a specific task by ID
@app.route('/tasks/<int:id>', methods=['GET'])
def get_task(id):
    task = Task.query.get(id)
    if task is None:
        return make_response(jsonify({'error': 'Task not found'}), 404)
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status
    })

# Create a new task
@app.route('/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if not data or 'title' not in data:
        return make_response(jsonify({'error': 'Bad request, title is required'}), 400)
    task = Task(title=data['title'],
                description=data.get('description', ''),
                status=data.get('status', 'pending'))
    db.session.add(task)
    db.session.commit()
    return jsonify({
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'status': task.status
    }), 201

# Update an existing task
@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    task = Task.query.get(id)
    if task is None:
        return make_response(jsonify({
            'error': 'No data provided'
        }), 400)
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.status = data.get('status', task.status)
    db.session.commit()
    return jsonify({'message': 'Task updated'})


# Delete an existing task
@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = Task.query.get(id)
    if task is None:
        return make_response(jsonify({'error': 'Task not found'}), 404)
    db.session.delete(task)
    db.session.commit()

    return jsonify({'messgae': 'Task deleted'})

if __name__ == '__main__':
    app.run(debug=True)


from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    return check_password_hash(hashed_password, password)

from .models import User

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return make_response(jsonify({'error': 'Username and password are required.'}), 400)

    # Check if the username is already taken
    if User.query.filter_by(username=username).first():
        return make_response(jsonify({'error': 'User already exists.'}), 400)

    # Create new user with a hashed password
    hashed_password = hash_password(password)
    new_user = User(username=username, password_hash=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully.'}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return make_response(jsonify({'error': 'Username and password are required.'}), 400)

    # Retrieve the user from the database
    user = User.query.filter_by(username=username).first()
    if user is None or not verify_password(user.password_hash, password):
        return make_response(jsonify({'error': 'Invalid username or password.'}), 401)

    # If valid, you could generate a token/session here
    return jsonify({'message': 'Logged in successfully.'})
