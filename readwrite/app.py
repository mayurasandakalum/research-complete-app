# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
import firebase_admin
from firebase_admin import credentials, firestore
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
from get_letters import get_text
from collections import Counter


app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"  # Stores session data locally
Session(app)

database = {"sathira": "123"}  # username: password

# Load the fine-tuned model and processor
model = WhisperForConditionalGeneration.from_pretrained(
    "./whisper-small-sinhala-finetuned"
)
processor = WhisperProcessor.from_pretrained("./whisper-small-sinhala-finetuned")
# Set the language and task
language = "Sinhala"
task = "transcribe"
# Update the model's generation configuration
model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(
    language=language, task=task
)
model.config.suppress_tokens = None

model_st = SentenceTransformer("Ransaka/bert-small-sentence-transformer")

UPLOAD_FOLDER = os.path.join("static", "aud_records")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Firebase
cred = credentials.Certificate("./learn-pal-firebase-adminsdk-ugedp-fcb865a7d8.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

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
    global model
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
    # Specify lang='si' for Sinhala
    tts = gTTS(text=text, lang="si")
    output_file = "./static/aud_records/tts_" + str(qid) + "_.wav"

    # Save the audio to a file
    tts.save(output_file)


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
        sin_text_to_speech(question, qid)
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
    correct = False
    audio_file = "./static/aud_records/" + str(Aud_data["ID"]) + ".wav"

    ans_txt = stt_sinhala(audio_file)
    user = session.get("user", "No user stored")
    if ans_txt:
        ori_answer = Aud_data["Answer"]
        sim = is_similar(ori_answer, ans_txt)
        print(sim, ori_answer)
        if sim > 0.6:
            correct = True
            Aud_results.append(Aud_data["Lesson"])
            db.collection("audio_results").add({"name": user, "data": Aud_data})

        return jsonify({"success": True, "correct": correct, "answer": ori_answer})
    else:
        AudQuestionID -= 1
        return (
            jsonify({"success": False, "message": "Speech to text model problem"}),
            404,
        )


@app.route("/save_audio", methods=["POST"])
def save_audio():
    audio = request.files.get("audio")
    question_id = request.form.get("questionID")
    if not audio or not question_id:
        return (
            jsonify({"success": False, "message": "Missing audio or question ID"}),
            400,
        )

    # Temporarily save the raw file
    raw_filename = f"{question_id}_raw"
    raw_filepath = os.path.join("static", "aud_records", raw_filename)
    audio.save(raw_filepath)

    # Convert raw (WebM/OGG) to WAV
    wav_filename = f"{question_id}.wav"
    wav_filepath = os.path.join("static", "aud_records", wav_filename)

    import subprocess

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
        ]
    )

    # Optionally remove the raw file
    os.remove(raw_filepath)

    return jsonify(
        {"success": True, "message": f"Audio file {wav_filename} saved successfully."}
    )


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
    if question_doc.exists:
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
        query = db.collection("audio_results").where("name", "==", user).stream()
        query2 = db.collection("write_results").where("name", "==", user).stream()
        res1 = calculate_res(query)
        res2 = calculate_res(query2)
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
    app.run(debug=True)
