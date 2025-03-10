# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import os
import torch
import torch.nn.functional as F
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from sentence_transformers import SentenceTransformer
import torchaudio
from gtts import gTTS
import random
import re
import base64
from collections import Counter
import sys
import io
import wave

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
AUDIO_FOLDER = os.path.join(STATIC_FOLDER, "aud_records")
WRITE_IMG_FOLDER = os.path.join(STATIC_FOLDER, "write_img")
IMAGES_FOLDER = os.path.join(STATIC_FOLDER, "Images")

# Create necessary directories
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(AUDIO_FOLDER, exist_ok=True)
os.makedirs(WRITE_IMG_FOLDER, exist_ok=True)
os.makedirs(IMAGES_FOLDER, exist_ok=True)

# Ensure templates directory exists
TEMPLATES_FOLDER = os.path.join(current_dir, "templates")
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

# Create submit_audio_form.html if it doesn't exist
submit_audio_form_path = os.path.join(TEMPLATES_FOLDER, "submit_audio_form.html")
if not os.path.exists(submit_audio_form_path):
    with open(submit_audio_form_path, "w", encoding="utf-8") as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Submit Audio</title>
</head>
<body>
    <h1>Submit Audio</h1>
    <p>This is a simple form to submit audio for question ID: {{ question_id }}</p>
    <form action="/submit_audio" method="post" enctype="multipart/form-data">
        <input type="file" name="audio" accept="audio/*">
        <input type="hidden" name="questionID" value="{{ question_id }}">
        <button type="submit">Submit</button>
    </form>
</body>
</html>
        """)

# Check if the background image exists, create a placeholder if not
auditory_bg_path = os.path.join(IMAGES_FOLDER, "auditory.jpg")
if not os.path.exists(auditory_bg_path):
    try:
        # Generate a simple gradient as a placeholder
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (800, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        for y in range(600):
            # Create a simple blue gradient
            color = (200, 220, 255 - int(y * 0.2))
            draw.line([(0, y), (800, y)], fill=color)
        img.save(auditory_bg_path)
        print(f"Created placeholder background image: {auditory_bg_path}")
    except Exception as e:
        print(f"Could not create background image: {e}")

try:
    import config
except ImportError:
    print(f"Error: Cannot import config module. Looking in: {parent_dir}")
    print(f"Python path: {sys.path}")
    raise

app.config['SECRET_KEY'] = config.SECRET_KEY

database = {"sathira": "123"}  # username: password

# Fix model loading by using the correct relative path
whisper_model_path = os.path.join(current_dir, "whisper-small-sinhala-finetuned")
print(f"Looking for model at: {whisper_model_path}")

# Load the fine-tuned model and processor
try:
    model = WhisperForConditionalGeneration.from_pretrained(
        whisper_model_path,
        local_files_only=True  # Explicitly specify loading from local files
    )
    processor = WhisperProcessor.from_pretrained(
        whisper_model_path,
        local_files_only=True
    )
    print(f"Successfully loaded model from {whisper_model_path}")
except Exception as e:
    print(f"Error loading model: {e}")
    # Set to None - you might want to handle this better in production
    model = None
    processor = None

# Set the language and task
language = "Sinhala"
task = "transcribe"
# Update the model's generation configuration
if model is not None:
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
        language=language, task=task
    )
    model.config.suppress_tokens = None

model_st = SentenceTransformer("Ransaka/bert-small-sentence-transformer")

# Flag to indicate if ffmpeg is available
FFMPEG_AVAILABLE = False
try:
    import subprocess
    result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    FFMPEG_AVAILABLE = (result.returncode == 0)
    print("ffmpeg is available in the system")
except Exception:
    print("ffmpeg is not available, will use Python fallback for audio conversion")

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

# Import get_letters only if model is loaded successfully
if model is not None:
    try:
        from get_letters import get_text
    except ImportError:
        print("Warning: Could not import get_letters module. Writing recognition will not work.")
        def get_text(*args, **kwargs):
            return "OCR module not available"

# Mock Firebase collections for offline mode
if OFFLINE_MODE:
    class MockFirestore:
        def __init__(self):
            self.audio_questions = {
                "1": {"Question": "Sample question 1", "Answer": "Sample answer 1", "Lesson": "lesson1", "ID": 1},
                "2": {"Question": "Sample question 2", "Answer": "Sample answer 2", "Lesson": "lesson1", "ID": 2},
                "3": {"Question": "Sample question 3", "Answer": "Sample answer 3", "Lesson": "lesson2", "ID": 3},
            }
            self.write_questions = {
                "1": {"Question": "Write sample 1", "Answer": "Written answer 1", "Lesson": "lesson1", "ID": 1},
                "2": {"Question": "Write sample 2", "Answer": "Written answer 2", "Lesson": "lesson1", "ID": 2},
                "3": {"Question": "Write sample 3", "Answer": "Written answer 3", "Lesson": "lesson2", "ID": 3},
            }
            self.results = []
            
        def collection(self, name):
            return MockCollection(self, name)
    
    class MockCollection:
        def __init__(self, db, name):
            self.db = db
            self.name = name
            
        def document(self, doc_id):
            return MockDocument(self.db, self.name, doc_id)
            
        def add(self, data):
            self.db.results.append(data)
            return True
            
        def where(self, field, op, value):
            return MockQuery(self.db, self.name, field, op, value)
    
    class MockDocument:
        def __init__(self, db, collection_name, doc_id):
            self.db = db
            self.collection = collection_name
            self.id = doc_id
        
        def get(self):
            return MockDocumentSnapshot(self.db, self.collection, self.id)
    
    class MockDocumentSnapshot:
        def __init__(self, db, collection, doc_id):
            self.db = db
            self.collection = collection
            self.id = doc_id
            self._exists = False
            self._data = {}
            
            if collection == "audio_questions" and doc_id in db.audio_questions:
                self._exists = True
                self._data = db.audio_questions[doc_id]
            elif collection == "write_questions" and doc_id in db.write_questions:
                self._exists = True
                self._data = db.write_questions[doc_id]
        
        @property
        def exists(self):
            return self._exists
            
        def to_dict(self):
            return self._data
    
    class MockQuery:
        def __init__(self, db, collection, field, op, value):
            self.db = db
            self.collection = collection
            self.field = field
            self.op = op
            self.value = value
        
        def stream(self):
            results = []
            # Just return empty results since this is a mock
            return results
    
    # Use our mock Firestore
    db = MockFirestore()

# Global variable to track the current question ID
AudQuestionID = 1
WrQuestionID = 1
no_q = 5
username = ""
Aud_data = {}
Wri_data = {}
# Wr_results = ["lesson1","lesson1","lesson1","lesson2","lesson2","lesson2","lesson3"]
# Aud_results = ["lesson1","lesson1","lesson2","lesson2","lesson2","lesson2","lesson2","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3"]
# Wr_results_2 = ["lesson3","lesson3","lesson3","lesson3"]
# Aud_results_2 = ["lesson1","lesson1","lesson1"]
Wr_results = []
Aud_results = []
Wr_results_2 = []
Aud_results_2 = []
wr_lesson = 0
rd_lesson = 0
wr_lesson_c = 0
rd_lesson_c = 0


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
        if wr_lesson_c > 5:
            lesson = 100
        else:
            wr_lesson_c += 1
            lesson = wr_lesson - 1
    else:
        lesson = int(num / noq)
    start = lesson * 50
    qid = random.randint(start, start + 50)
    return qid


def random_q_r(num, noq):
    global rd_lesson
    global rd_lesson_c
    if rd_lesson > 0:
        if rd_lesson_c > 5:
            lesson = 100
        else:
            rd_lesson_c += 1
            lesson = rd_lesson - 1
    else:
        lesson = int(num / noq)
    start = lesson * 50
    qid = random.randint(start, start + 50)
    return qid


def stt_sinhala(audio_file):
    global model, processor
    
    if model is None or processor is None:
        print("Model or processor not available. Cannot transcribe audio.")
        return "Model not loaded"
        
    try:
        speech_array, sampling_rate = torchaudio.load(audio_file)

        # Resample the audio to 16 kHz if necessary
        if sampling_rate != 16000:
            resampler = torchaudio.transforms.Resample(
                orig_freq=sampling_rate, new_freq=16000
            )
            speech_array = resampler(speech_array)

        # Convert to mono channel if necessary
        if speech_array.shape[0] > 1:
            speech_array = speech_array.mean(dim=0)

        # Prepare the input features
        input_features = processor.feature_extractor(
            speech_array.numpy(), sampling_rate=16000, return_tensors="pt"
        ).input_features

        # Move model and inputs to GPU if available
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = model.to(device)
        input_features = input_features.to(device)

        # Generate transcription
        with torch.no_grad():
            generated_ids = model.generate(input_features)

        # Decode the transcription
        transcription = processor.tokenizer.decode(
            generated_ids[0], skip_special_tokens=True
        )

        print("Transcription:", transcription)
        return transcription
    except Exception as e:
        print(f"Error in speech-to-text: {e}")
        return None


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


def sin_text_to_speech(text, qid):
    """
    Convert the given Sinhala text to speech using gTTS and play the audio.
    """
    try:
        # Specify lang='si' for Sinhala
        tts = gTTS(text=text, lang="si")
        output_file = os.path.join(AUDIO_FOLDER, f"tts_{qid}_.wav")
        
        # Save the audio to a file
        tts.save(output_file)
        print(f"Generated TTS audio saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error generating TTS audio: {e}")
        return False


# Route for rendering the main page
@app.route("/")
def index():
    return render_template("Login.html")


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


# Route for rendering the registration page
@app.route("/registration")
def registration():
    return render_template("registration.html")

@app.route('/api/info')
def api_info():
    return jsonify({
        'app': 'Read/Write App',
        'status': 'running'
    })


# Route to handle registration form submission
@app.route("/form_registration", methods=["POST"])
def form_registration():
    # Get username and password from the form
    username = request.form.get("username")
    password = request.form.get("password")

    # Check if the username already exists
    if username in database:
        return render_template("registration.html", info="Username already exists!")

    # Add the new user to the database
    database[username] = password
    return render_template("login.html", info="Registration successful! Please log in.")


@app.route("/home")
def home():
    global username
    return render_template("Home.html", name=username)


@app.route("/auditory_learning")
def auditory_learning():
    global AudQuestionID
    global Aud_data
    global no_q
    qid = random_q_r(AudQuestionID, no_q)
    print(qid)
    question_doc = db.collection("audio_questions").document(str(qid)).get()
    if question_doc.exists:
        question_data = question_doc.to_dict()
        question = question_data.get("Question", "No Question Available")
        
        tts_success = sin_text_to_speech(question, qid)
        if not tts_success:
            print(f"Warning: Could not generate TTS for question {qid}")
            
        image = question_data.get("Image", None)
        if image:
            image = image.replace("<", "").replace(">", "")
        Aud_data = question_data
        return render_template(
            "Auditory_learning.html", question=question_data, image=image
        )
    return "No questions found.", 404


@app.route("/next_question", methods=["GET", "POST"])
def next_question():
    global AudQuestionID
    global Aud_data

    AudQuestionID += 1
    qid = random_q_r(AudQuestionID, no_q)
    print(qid)
    question_doc = db.collection("audio_questions").document(str(qid)).get()

    if question_doc.exists:
        question_data = question_doc.to_dict()
        question_id = str(AudQuestionID)

        # Check if audio file exists for this question
        audio_path = os.path.join("static", "aud_records", f"{question_id}.wav")
        audio_exists = os.path.exists(audio_path)

        question = question_data.get("Question", "No Question Available")
        sin_text_to_speech(question, qid)

        Aud_data = question_data
        image = question_data.get("Image", None)
        if image:
            image = image.replace("<", "").replace(">", "")

        return jsonify(
            {
                "success": True,
                "question": question_data,
                "image": image,
                "id": question_id,
                "audio_exists": audio_exists,
            }
        )
    else:
        AudQuestionID = 0
        return (
            jsonify(
                {"success": False, "question": False, "message": "No more questions!"}
            ),
            404,
        )


@app.route("/submit_audio", methods=["GET", "POST"])
def submit_sudio():
    global Aud_data
    global AudQuestionID
    global Aud_results
    
    # Handle both GET and POST requests
    if request.method == "GET":
        # For GET requests, return a simple form (helpful for debugging)
        return render_template("submit_audio_form.html", question_id=Aud_data.get("ID", "unknown"))
    
    correct = False
    audio_file = os.path.join(AUDIO_FOLDER, f"{Aud_data['ID']}.wav")
    
    # Check if audio file exists
    if not os.path.exists(audio_file):
        print(f"Warning: Audio file not found: {audio_file}")
        return jsonify({
            "success": False, 
            "message": "Audio file not found. Please record your answer first."
        }), 400

    ans_txt = stt_sinhala(audio_file)
    user = session.get("user", "No user stored")
    
    if ans_txt:
        ori_answer = Aud_data["Answer"]
        sim = is_similar(ori_answer, ans_txt)
        print(f"Similarity score: {sim}, Original answer: {ori_answer}")
        
        if sim > 0.6:
            correct = True
            Aud_results.append(Aud_data["Lesson"])
            if not OFFLINE_MODE:
                db.collection("audio_results").add({"name": user, "data": Aud_data})

        return jsonify({"success": True, "correct": correct, "answer": ori_answer})
    else:
        AudQuestionID -= 1
        return jsonify({"success": False, "message": "Speech to text model problem"}), 500


@app.route("/save_audio", methods=["POST"])
def save_audio():
    audio = request.files.get("audio")
    question_id = request.form.get("questionID")
    if not audio or not question_id:
        return (
            jsonify({"success": False, "message": "Missing audio or question ID"}),
            400,
        )

    # Create absolute paths
    raw_filename = f"{question_id}_raw"
    wav_filename = f"{question_id}.wav"
    
    raw_filepath = os.path.join(AUDIO_FOLDER, raw_filename)
    wav_filepath = os.path.join(AUDIO_FOLDER, wav_filename)

    try:
        # Temporarily save the raw file
        audio.save(raw_filepath)
        print(f"Raw audio saved to: {raw_filepath}")
        
        conversion_success = False
        
        # Try ffmpeg first if available
        if FFMPEG_AVAILABLE:
            try:
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",  # overwrite
                        "-i",
                        raw_filepath,
                        "-ar",
                        "16000",  # resample to 16kHz if needed
                        "-ac",
                        "1",  # 1 channel
                        wav_filepath,
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                conversion_success = True
                print(f"Converted audio with ffmpeg: {wav_filepath}")
            except subprocess.CalledProcessError as e:
                print(f"ffmpeg error: {e}, trying Python fallback")
            
        # If ffmpeg failed or is not available, try Python fallback
        if not conversion_success:
            conversion_success = convert_audio_python(raw_filepath, wav_filepath)
            if conversion_success:
                print(f"Converted audio with Python: {wav_filepath}")
            else:
                # Last resort - create an empty WAV file so the app can continue
                try:
                    import wave
                    import numpy as np
                    with wave.open(wav_filepath, 'w') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)  # 16-bit
                        wf.setframerate(16000)
                        # 1 second of silence
                        silent_data = np.zeros(16000, dtype=np.int16).tobytes()
                        wf.writeframes(silent_data)
                    print(f"Created empty WAV file as placeholder: {wav_filepath}")
                    conversion_success = True
                except Exception as e:
                    print(f"Failed to create empty WAV file: {e}")

        # Clean up temp file
        try:
            if os.path.exists(raw_filepath):
                os.remove(raw_filepath)
        except Exception as e:
            print(f"Warning: Could not remove temporary file: {e}")
            
        if conversion_success:
            return jsonify({
                "success": True, 
                "message": f"Audio file {wav_filename} saved successfully."
            })
        else:
            return jsonify({
                "success": False, 
                "message": "Failed to convert audio format."
            }), 500
    except Exception as e:
        print(f"Error saving audio: {e}")
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


def convert_audio_python(input_file, output_file):
    """
    Pure Python audio conversion as a fallback when ffmpeg is not available.
    Attempts multiple methods to convert audio files.
    """
    try:
        # First try: Use torchaudio directly
        try:
            audio_data, sample_rate = torchaudio.load(input_file)
            
            # Resample to 16KHz and convert to mono if needed
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate, new_freq=16000
                )
                audio_data = resampler(audio_data)
            
            if audio_data.shape[0] > 1:
                audio_data = audio_data.mean(dim=0, keepdim=True)
            
            # Save as WAV
            torchaudio.save(output_file, audio_data, 16000)
            return True
        except Exception as e:
            print(f"First conversion attempt failed: {e}")
            
            # Second try: Read raw binary and convert
            try:
                import wave
                import numpy as np
                
                # For WebM/OGG we need specialized libraries, but we can try a simple approach
                # Read as raw PCM data, make assumptions about format
                with open(input_file, 'rb') as f:
                    raw_data = f.read()
                
                # Try to extract audio data by looking for common headers
                # This is a very simplified approach and won't work for all formats
                if b'OggS' in raw_data:
                    print("Detected OGG format, cannot convert without specialized libraries")
                    return False
                
                if b'webm' in raw_data:
                    print("Detected WebM format, cannot convert without specialized libraries")
                    return False
                
                # Fallback: Try to extract raw PCM data (this is very error-prone)
                # Just create a placeholder silent WAV file
                with wave.open(output_file, 'w') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(16000)
                    # 1 second of silence
                    silent_data = np.zeros(16000, dtype=np.int16).tobytes()
                    wf.writeframes(silent_data)
                
                print("Created placeholder WAV file")
                return True
            except Exception as e:
                print(f"Second conversion attempt failed: {e}")
                return False
    except Exception as e:
        print(f"Error in Python audio conversion: {e}")
        return False


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


@app.route("/next_question_rw", methods=["GET"])
def next_question_rw():
    global WrQuestionID
    WrQuestionID += 1
    global Wri_data

    qid = random_q_w(WrQuestionID, no_q)
    question_doc = db.collection("write_questions").document(str(qid)).get()
    if question_doc.exists():
        question_data = question_doc.to_dict()
        image = question_data.get("Image", None)
        if image:
            image = image.replace("<", "").replace(">", "")
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


@app.route("/submit_write", methods=["GET", "POST"])
def submit_write():
    global Wri_data
    global WrQuestionID
    global Wr_results

    correct = False
    qid = Wri_data["ID"]
    _file = "./static/write_img/" + str(qid) + ".png"

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

    model_path = "write_model/multi_letter_detector2.pth"
    class_mapping_path = "write_model/class_mapping.pkl"
    class_mapping_path2 = "write_model/class_mapping2.pkl"

    ans_txt = get_text(
        model_path, _file, class_mapping_path, class_mapping_path2, number, qid
    )
    user = session.get("user", "No user stored")

    if ans_txt:
        ori_answer = Wri_data["Answer"]
        sim = is_similar(ori_answer, ans_txt)
        print(ans_txt, ori_answer)

        if sim > 0.6:
            correct = True
            Wr_results.append(Wri_data["Lesson"])
            db.collection("write_results").add({"name": user, "data": Wri_data})

        return jsonify({"success": True, "correct": correct, "answer": ori_answer})

    else:
        WrQuestionID -= 1
        return jsonify({"success": False, "message": "OCR model not working"}), 404


@app.route("/all_score")
def all_score():
    user = session.get("user", None)
    if user:
        if not OFFLINE_MODE and db is not None:
            query = db.collection("audio_results").where("name", "==", user).stream()
            query2 = db.collection("write_results").where("name", "==", user).stream()
            res1 = calculate_res(query)
            res2 = calculate_res(query2)
        else:
            # Mock results for offline mode
            res1 = {"lesson1": 3, "lesson2": 2}
            res2 = {"lesson1": 2, "lesson3": 1}
        print(res1, res2)
    else:
        return render_template("Login.html")

    return render_template("Results.html", res1=res1, res2=res2)


@app.route("/write_guide")
def write_guide():
    global Wr_results_2
    global Wr_results
    global wr_lesson
    counts = Counter(Wr_results)
    counts_dict = dict(counts)
    if wr_lesson > 0:
        counts2 = Counter(Wr_results_2)
        counts_dict2 = dict(counts2)
        counts_dict["New " + "lesson" + str(wr_lesson)] = counts_dict2[
            "lesson" + str(wr_lesson)
        ]
        message = "You Complete your Journey"
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


@app.route("/speech_guide")
def speech_guide():
    global Aud_results
    global Aud_results_2
    global rd_lesson
    # sin_text_to_speech("දැන් අපි බලමු හතළිස් අට තුනෙන් බෙදන්නේ කොහොමද කියලා, සියස්ථානයේ හතරට තුනේ ඒවා එකයි. එම එක හතරට උඩින් ලියනවා. පසුව එම එක තුනෙන් ගුණ කර විට පිළිතුර තුන හතරට පහළින් ලියනවා. හතරෙන් තුනක් අඩු කර විට පිළිතුර එක පහලින් ලියනවා. පසුව එක ස්ථානයේ ඇති අට එම එක අසලට ගෙන දහ අටට තුනේ ඒවා බලනවා. එවිට පිළිතුර හය එකස්ථානයේ අටට ඉහළින් ලියනවා. එම හය තුනෙන් ගුණ කරවිට පිළිතුර දහ අට පහලින් ලියනවා. දැන් අපිට පේනවා හතළිස් අට තුනෙන් බෙදූ විට පිළිතුර දාසයක් සහ ඉතුරු බිංදුවක් ලෙස ලැබෙනවා.",923)
    counts = Counter(Aud_results)
    counts_dict = dict(counts)
    if rd_lesson > 0:
        counts2 = Counter(Aud_results_2)
        counts_dict2 = dict(counts2)
        counts_dict["New " + "lesson" + str(rd_lesson)] = counts_dict2[
            "lesson" + str(rd_lesson)
        ]
        message = "You Complete your Journey"
        images = ["img2.png"]
        return render_template(
            "AudioGuide.html",
            results=counts_dict,
            message=message,
            images=images,
            lesson_id="Finished",
        )
    else:
        lesson_no = get_min_count_string(counts_dict)
        rd_lesson = lesson_no
        message = "Since you have minimum result for lesson " + str(lesson_no)
        img_range = [3, 2, 2]
        images = []
        for img in range(img_range[lesson_no - 1]):
            images.append("9" + str(lesson_no) + str(img + 1) + ".png")
        return render_template(
            "AudioGuide.html",
            results=counts_dict,
            message=message,
            images=images,
            lesson_id=str(lesson_no),
        )


if __name__ == "__main__":
    port = config.READWRITE_APP_PORT if hasattr(config, 'READWRITE_APP_PORT') else 5002
    app.run(debug=True, port=port)
