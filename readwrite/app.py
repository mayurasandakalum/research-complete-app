# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os
import torch
import torch.nn.functional as F
from sentence_transformers import SentenceTransformer
import random
import re
import base64
from write_model.get_letters import get_text
from collections import Counter
import sys
import io
import wave
import config

# Initialize the app with template and static folder configurations
app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"  # Stores session data locally
Session(app)

# Fix the import mechanism for the config module
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)  # Use insert instead of append to prioritize this path

# Make all paths absolute for consistency
STATIC_FOLDER = os.path.join(current_dir, "static")
WRITE_IMG_FOLDER = os.path.join(STATIC_FOLDER, "write_img")
IMAGES_FOLDER = os.path.join(STATIC_FOLDER, "Images")

# Create necessary directories
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(WRITE_IMG_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Ensure templates directory exists
TEMPLATES_FOLDER = os.path.join(current_dir, "templates")
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

database = {"isu": "123"}  # username: password


model_st = SentenceTransformer("Ransaka/bert-small-sentence-transformer")

# Flag to indicate if we're running with Firebase or in offline mode
OFFLINE_MODE = False

# Initialize Firebase with better error handling
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    
    firebase_cred_path = os.path.join(current_dir, "learn-pal-firebase-adminsdk-ugedp-fcb865a7d8.json")
    if os.path.exists(firebase_cred_path):
        cred = credentials.Certificate(firebase_cred_path)
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        print(f"Successfully initialized Firebase with credentials from {firebase_cred_path}")
    else:
        print(f"Firebase credentials file not found at {firebase_cred_path}")
        print("Running in OFFLINE MODE - Firebase features will be simulated")
        OFFLINE_MODE = True
        db = None
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    print("Running in OFFLINE MODE - Firebase features will be simulated")
    OFFLINE_MODE = True
    db = None


# Global variable to track the current question ID
WrQuestionID = 1
no_q = 5
username = ""
Wri_data = {}
# Wr_results = ["lesson1","lesson1","lesson1","lesson2","lesson2","lesson2","lesson3"]
# Wr_results_2 = ["lesson3","lesson3","lesson3","lesson3"]

Wr_results = []
Wr_results_2 = []
wr_lesson = 0
wr_lesson_c = 0


def extract_first_number(s):
    match = re.search(r"\d+", s)
    return int(match.group()) if match else None


def get_min_count_string(strings):
    counter = Counter(strings)
    min_count = min(counter.values())
    min_strings = [s for s, count in counter.items() if count == min_count]
    no = extract_first_number(min_strings[0])
    return no


def calculate_res(query):
    result = []
    for doc in query:
        data_dict = doc.to_dict()
        result.append(data_dict["data"]["Lesson"])
    counts = Counter(result)
    counts_dict = dict(counts)
    return counts_dict


def random_q_w(num, noq):
    global wr_lesson
    global wr_lesson_c
    if wr_lesson > 0:
        if wr_lesson_c > 4:
            lesson = 100
        else:
            wr_lesson_c = wr_lesson_c + 1    
            lesson = wr_lesson-1
    else:
        lesson = int((num-1)/noq)
    start = lesson * 50
    qid = random.randint(start, start + 50)
    return qid



def is_similar(target, source):
    sentences = [target, source]

    if target in source:
        return 0.75

    embeddings = model_st.encode(sentences, convert_to_tensor=True)
    # Compute Cosine Similarity using torch
    similarity = F.cosine_similarity(
        embeddings[0].unsqueeze(0), embeddings[1].unsqueeze(0)
    )

    return similarity

# Route for rendering the main page
# @app.route("/")
# def index():
#     return render_template("Login.html")

@app.route("/logout")
def logout():
    session["user"] = ""
    return render_template("Login.html")


# Route to handle login
@app.route("/form_login", methods=["POST", "GET"])
def login():
    # Get username and password from the form
    username = request.form.get("username")
    password = request.form.get("password")

    # Validate credentials
    if username not in database:
        return render_template("login.html", info="Invalid Username")
    elif database[username] != password:
        return render_template("login.html", info="Invalid Password")
    else:
        session["user"] = username
        return render_template("Home.html", name=username)

@app.route('/api/info')
def api_info():
    return jsonify({
        'app': 'Read/Write App',
        'status': 'running'
    })

@app.route("/")
def home():
    global username
    return render_template("Home.html", name=username)

#Fetches a random question from Firebase and displays it.
@app.route("/reading_writing_learning")
def reading_writing_learning():
    global WrQuestionID
    global Wri_data

    qid = random_q_w(WrQuestionID, no_q)
    question_doc = db.collection("write_questions").document(str(qid)).get()
    if question_doc.exists:
        question_data = question_doc.to_dict()
        image = question_data.get("Image", None)
        if image:
            image = image.replace("<", "").replace(">", "")
        Wri_data = question_data
        return render_template("R&W_learning.html", question=question_data, image=image)

    return "No questions found.", 404

#returns the next writing question
@app.route("/next_question_rw", methods=["GET"])
def next_question_rw():
    global WrQuestionID
    WrQuestionID += 1
    global Wri_data

    qid = random_q_w(WrQuestionID, no_q)
    question_doc = db.collection("write_questions").document(str(qid)).get()#retrieve the question from db
    if question_doc.exists:
        question_data = question_doc.to_dict()
        image = question_data.get("Image", None)
        if image:
            image = image.replace("<", "").replace(">", "")# If an image is associated with the question, it is cleaned of unwanted characters.
        Wri_data = question_data
        return jsonify(
            {
                "success": True,
                "question": question_data,
                "image": image,
            }
        )
    else:
        # If no more questions, reset ID or handle accordingly
        WrQuestionID = 0  # Decrement ID to stay on the last valid question
        return (
            jsonify(
                {"success": False, "question": False, "message": "No more questions!"}
            ),
            404,
        )
        
# how many characters match and checks if they meet the 75% threshold.
def is_75_percent_match(str1: str, str2: str) -> bool:
    """
    Checks if at least 75% of the letters in one string match another string.
    
    Args:
        str1 (str): First input string.
        str2 (str): Second input string.
    
    Returns:
        bool: True if 75% or more of the characters match, False otherwise.
    """
    # Convert strings to lowercase to make the comparison case-insensitive
    str1, str2 = str1.lower(), str2.lower()
    
    # Count character occurrences in both strings
    counter1, counter2 = Counter(str1), Counter(str2)
    
    # Calculate total matching characters
    match_count = sum((counter1 & counter2).values())
    
    # Determine the percentage of matching characters
    required_match = max(len(str1), len(str2)) * 0.75
    
    return match_count >= required_match

@app.route("/submit_write", methods=["GET", "POST"])
def submit_write():
    global Wri_data
    global WrQuestionID
    global Wr_results
    global wr_lesson
    global Wr_results_2

    correct = False
    qid = Wri_data["ID"]
    _file = "./readwrite/static/write_img/" + str(qid) + ".png"

    data = request.get_json()
    image_data = data.get("image")
    number = data.get("number")

    if not image_data:
        return jsonify({"message": "No image data received."}), 400

    # Remove the data URL prefix (data:image/png;base64,)
    image_data = re.sub("^data:image/.+;base64,", "", image_data)
    image_binary = base64.b64decode(image_data)
    # Save the file
    with open(_file, "wb") as f:
        f.write(image_binary)

    model_path = "readwrite/write_model/multi_letter_detector2.pth"
    class_mapping_path = "readwrite/write_model/class_mapping.pkl"
    class_mapping_path2 = "readwrite/write_model/class_mapping2.pkl"

    #The OCR model  reads the text from the image
    ans_txt = get_text(
        model_path, _file, class_mapping_path, class_mapping_path2, number, qid
    )
    user = session.get("user", "No user stored")

    #The extracted answer is compared to the correct answer
    if ans_txt:
        ori_answer = Wri_data["Answer"]
        sim = is_similar(ori_answer, ans_txt)
        print(ans_txt,"===",ori_answer,"===",sim)

        if sim> 0.7 or is_75_percent_match(ori_answer,ans_txt):
            if wr_lesson > 0: 
                correct = True
                Wr_results_2.append(Wri_data['Lesson'])
            else:
                correct = True
                Wr_results.append(Wri_data['Lesson'])
                     
            db.collection('write_results').add({"name":user,"data":Wri_data}) #The correct answers are stored in db
           
        return jsonify({
            'success': True,
            'correct': correct,
            'answer':ori_answer
        })

    else:
        WrQuestionID -= 1
        return jsonify({"success": False, "message": "OCR model not working"}), 404


@app.route("/write_guide")
def write_guide():
    global Wr_results_2
    global Wr_results
    global wr_lesson
    counts = Counter(Wr_results)
    counts_dict = dict(counts)
    
    #counts the number of correct answers per lesson.
    if wr_lesson > 0:
        if len(Wr_results_2) == 0:
            counts_dict["New Results"]=0
            message="Get lost u looser"
        else:    
            counts2 = Counter(Wr_results_2)
            counts_dict2 = dict(counts2)
            print(counts_dict2)
            counts_dict["New "+"lesson"+str(wr_lesson)]=counts_dict2["lesson0"+str(wr_lesson)]
            message="You Complete your Journey"
        images = ["img2.png"]
        return render_template(
            "WriteGuide.html",
            results=counts_dict,
            message=message,
            images=images,
            lesson_id="Finished",
        )
    else:
        lesson_no = get_min_count_string(counts_dict)
        wr_lesson = lesson_no
        message = "Since you have minimum result for lesson " + str(lesson_no)
        img_range = [2, 3, 3]
        images = []
        for img in range(img_range[lesson_no - 1]):
            images.append(str(lesson_no) + str(img + 1) + ".png")
        return render_template(
            "WriteGuide.html",
            results=counts_dict,
            message=message,
            images=images,
            lesson_id=str(lesson_no),
        )

if __name__ == "__main__":
    port = config.READWRITE_APP_PORT if hasattr(config, 'READWRITE_APP_PORT') else 5002
    app.run(debug=True, port=port)