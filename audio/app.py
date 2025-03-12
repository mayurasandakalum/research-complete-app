# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, session
from flask_session import Session
# import firebase_admin
# from firebase_admin import credentials, firestore
import os
import sys

# Fix the import mechanism for the config module - MOVED THIS UP
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)  # Use insert instead of append to prioritize this path

import config  # Now this will work

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
import io
import wave

# Initialize the app with template and static folder configurations
app = Flask(__name__)
app.config["SESSION_TYPE"] = "filesystem"  # Stores session data locally
Session(app)

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


# app.config['SECRET_KEY'] = config.SECRET_KEY

database = {"tharushi": "123"}  # username: password


# Load the fine-tuned model and processor
model = WhisperForConditionalGeneration.from_pretrained("audio/whisper-small-sinhala-finetuned")
processor = WhisperProcessor.from_pretrained("audio/whisper-small-sinhala-finetuned")
# Set the language and task
language = "Sinhala"
task = "transcribe"
# Update the model's generation configuration
model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language=language, task=task)
model.config.suppress_tokens = None

model_st = SentenceTransformer("Ransaka/bert-small-sentence-transformer")

UPLOAD_FOLDER = os.path.join('static', 'aud_records')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Firebase
# cred = credentials.Certificate(".audio/learn-pal-firebase-adminsdk-ugedp-fcb865a7d8.json")
# firebase_admin.initialize_app(cred)
# db = firestore.client()

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
AudQuestionID = 1
no_q = 5
username = ""
Aud_data = {}
# Aud_results = ["lesson1","lesson1","lesson2","lesson2","lesson2","lesson2","lesson2","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3","lesson3"]
# Aud_results_2 = ["lesson1","lesson1","lesson1"]
Aud_results = []
Aud_results_2 = []
rd_lesson = 0
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
        resampler = torchaudio.transforms.Resample(orig_freq=sampling_rate, new_freq=16000)
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
    transcription = processor.tokenizer.decode(generated_ids[0], skip_special_tokens=True)

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


def sin_text_to_speech(text,qid):
    """
    Convert the given Sinhala text to speech using gTTS and play the audio.
    """
    # Specify lang='si' for Sinhala
    tts = gTTS(text=text, lang='si')
    output_file = "./audio/static/aud_records/tts_"+str(qid)+"_.wav"
    
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

@app.route('/api/info')
def api_info():
    return jsonify({
        'app': 'Audio App',
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


@app.route('/auditory_learning')
def auditory_learning():
    global AudQuestionID
    global Aud_data
    global no_q
    qid=random_q_r(AudQuestionID,no_q)
    print(qid)
    question_doc = db.collection('audio_questions').document(str(qid)).get()
    if question_doc.exists:
        question_data = question_doc.to_dict()
        question = question_data.get('Question', 'No Question Available')
        sin_text_to_speech(question,qid)
        image = question_data.get('Image', None)
        if image:
            image=image.replace("<","").replace(">","")
        Aud_data=question_data
        return render_template('Auditory_learning.html', question=question_data, image=image)
    return "No questions found.", 404


@app.route('/next_question', methods=['GET','POST'])
def next_question():
    global AudQuestionID
    global Aud_data
    
    AudQuestionID += 1
    qid=random_q_r(AudQuestionID,no_q)
    print(qid)
    question_doc = db.collection('audio_questions').document(str(qid)).get()

    if question_doc.exists:
        question_data = question_doc.to_dict()
        question_id = str(AudQuestionID)

        # Check if audio file exists for this question
        audio_path = os.path.join('static', 'aud_records', f"{question_id}.wav")
        audio_exists = os.path.exists(audio_path)
        
        question = question_data.get('Question', 'No Question Available')
        sin_text_to_speech(question,qid)
        
        Aud_data=question_data
        image = question_data.get('Image', None)
        if image:
            image=image.replace("<","").replace(">","")
            
        
        return jsonify({
            'success': True,
            'question': question_data,
            'image': image,
            'id': question_id,
            'audio_exists': audio_exists,
        })
    else:
        AudQuestionID = 0
        return jsonify({'success': False,'question': False ,'message': 'No more questions!'}), 404


@app.route('/submit_audio', methods=['GET','POST'])
def submit_sudio():
    global Aud_data
    global AudQuestionID
    global Aud_results
    global rd_lesson
    global Aud_results_2

    correct = False
    audio_file = "static/aud_records/"+str(Aud_data['ID'])+".wav"

    ans_txt=stt_sinhala(audio_file)
    user=session.get('user', 'No user stored')
    if ans_txt:
        ori_answer=Aud_data['Answer']
        sim=is_similar(ori_answer,ans_txt)
        print(sim,ori_answer)
        if sim> 0.6:
            if rd_lesson > 0: 
                correct = True
                Aud_results_2.append(Aud_data['Lesson'])
            else:
                correct = True
                Aud_results.append(Aud_data['Lesson'])     
            db.collection('audio_results').add({"name":user,"data":Aud_data})

        print(Aud_results_2)
        print(Aud_results)    
           
        return jsonify({
            'success': True,
            'correct': correct,
            'answer':ori_answer
        })
    else:
        AudQuestionID -= 1
        return jsonify({'success': False, 'message': 'Speech to text model problem'}), 404    



@app.route('/save_audio', methods=['POST'])
def save_audio():
    audio = request.files.get('audio')
    question_id = request.form.get('questionID')
    if not audio or not question_id:
        return jsonify({'success': False, 'message': 'Missing audio or question ID'}), 400

    # Temporarily save the raw file
    raw_filename = f"{question_id}_raw"
    raw_filepath = os.path.join(os.getcwd(),'static', 'aud_records', raw_filename)
    audio.save(raw_filepath)

    # Convert raw (WebM/OGG) to WAV
    wav_filename = f"{question_id}.wav"
    wav_filepath = os.path.join(os.getcwd(),'static', 'aud_records', wav_filename)

    import subprocess
    subprocess.run([
        "ffmpeg",
        "-y",  # overwrite
        "-i", raw_filepath,
        "-ar", "16000",  # resample to 16kHz if needed
        "-ac", "1",      # 1 channel
        wav_filepath
    ])

    # Optionally remove the raw file
    os.remove(raw_filepath)

    return jsonify({'success': True, 'message': f'Audio file {wav_filename} saved successfully.'})


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


@app.route('/speech_guide')
def speech_guide():
    global Aud_results
    global Aud_results_2
    global rd_lesson
    sin_text_to_speech("යම්කිසි රූපයකින් බාගයක් එනම් දෙකෙන් එකක්, දෙකෙන් පංගුව පහත රූපයේ පරිදි පෙන්විය හැක.",911)
    sin_text_to_speech("යම්කිසි රූපයකින් හතරෙන් පංගු පහත රූපයේ පරිදි දැක්විය හැක.",912)
    sin_text_to_speech("අපි දැන් බලමු මල් දොලහකින් හතරෙන් පංගු හඳුනාගන්න. මල් දොළහකින් හතරෙන් එකක මල් තුනක් තියෙනවා.මල් දොළහකින් හතරෙන් දෙකක මල් හයක් තියෙනවා.මල් දොළහකින් හතරෙන් තුනක මල් නවයක් තියෙනවා. ",913)
    # sin_text_to_speech("අපි බලමු ඉලක්කම් තුනේ සංඛ්‍යාවක් ගුණ කරන්නේ කොහොමද කියලා, ඒ සඳහා උදාහරණයක් ලෙස හාරසිය තිස් අට, දෙකෙන් ගුණ කරලා බලමු. අට දෙකෙන් ගුණකර විට දාසයයි. එවිට හය එකස්ථානයේ ලියා එක දහස් ස්ථානයට රැගෙන යයි. පසුව දෙක තුනෙන් ගුණ කරවිට හයයි. දහස්තානයේ ඉතුරු වූ එකත් සමග හතයි. එවිට හත දහස් ස්ථානයේ ලියයි. දෙක හතරෙන් ගුණ කර විට අටයි. එවිට අට සිය ස්ථානයේ ලියයි. එවිට පිළිතුර අටසිය හැත්ත හයයි.",921)
    # sin_text_to_speech("ඉහත ආකාරයටම දෙසීය තිස් දෙක, හතරෙන් ගුණ කර විට පිළිතුර පහත පරිදි නවසිය විසි අට ලැබේ.",922)
    # sin_text_to_speech("අපි දැන් බලමු හාරසිය විසිතුන, හයෙන් ගුණකර. හය තුනෙන් ගුණ කරවිට දහ අටයි. එවිට අට එකස්ථානයේ ලියා එක දහස්තානයට රැගෙන යයි. හය දෙක තුනෙන් ගුණ කර විට දහ අටයි. දහස්තානයේ ඉතිරි වූ එකත් සමඟ දහතුනයි. එවිට තුන දහස් ස්ථානයේ ලියා එක සියස්ථානයට රැගෙන යයි. හය හතරෙන් ගුණ කර විට විසිහතරයි. සියස්ථානයේ ඉතිරි එකත් සමග විසි පහයි. එවිට පහා සියස්ථානයේලියා දෙක දාහස් ස්ථානයට රැගෙනයයි. පිළිතුර දෙදහස් පන්සිය තිස් අටයි.",923)
    # sin_text_to_speech("ඉහත ආකාරයටම දෙසිය පනස්තුන හතෙන් ගුණ කර විට පහත පරිදි පිළිතුර එක්දහස් හත්සිය හැත්තෑ එකක් ලැබේ..",924)
    # sin_text_to_speech("අපි දැන් බලමු පන්සිය හතලිස් අට, අටෙන් ගුණ කරලා.අට අටෙන් ගුණ කර විට හැට හතරයි. හතර එකස්ථානයේලියා හය දහස්තානයට රැගෙන යයි. අට හතරෙන් ගුණ කර වෙත තිස් දෙකයි. දහස්තානයේ ඉතිරි හයත් සමඟ තිස් අටයි. අට දහස්තානයේ ලියා තුන සියස්ථානයට රැගෙන යයි. අට පහෙන් ගුණ කරවිට හතළිහයි. සියස්ථානයේ ඉතිරි තුනත් සමඟ හතළිස් තුනයි. තුන සියස්ථානයේ ලියා හතර දාහස්ථානයේ ලියයි. එවිට පිළිතුර හාර දහස් තුන්සිය අසූ හතරයි.",925)
    # sin_text_to_speech("ඉහත ආකාරයට දෙසිය පනස් තුන නවයෙන් ගුණ කර විට දෙදහස් දෙසිය හැත්ත හතක් ලැබේ.",926)
    # sin_text_to_speech("අපි බෙදීම උදාහරණවලින් ඉගෙන ගනිමු. මුලින්ම අපි දෙකෙන් බෙදන්න ඉගෙන ගමු. දෙසිය විසි හය , දෙකෙන් බෙදන්න ඉගෙන ගමු. පහත ආකාරයට අපිට දෙකෙන් බෙදන්න පුළුවන්. එවිට පිළිතුර එකසිය දහතුනයි.",931)
    # sin_text_to_speech("දැන් අපි බලමු හතළිස් අට තුනෙන් බෙදන්නේ කොහොමද කියලා.සියස්ථානයේ හතරට තුනේ ඒවා එකයි. එම එක හතරට උඩින් ලියනවා. පසුව එම එක තුනෙන් ගුණ කර විට පිළිතුර තුන හතරට පහළින් ලියනවා. හතරෙන් තුනක් අඩු කර විට පිළිතුර එක පහලින් ලියනවා. පසුව එක ස්ථානයේ ඇති අට එම එක අසලට ගෙන දහ අටට තුනේ ඒවා බලනවා. එවිට පිළිතුර හය එකස්ථානයේ අටට ඉහළින් ලියනවා. එම හය තුනෙන් ගුණ කරවිට පිළිතුර දහ අට පහලින් ලියනවා. දැන් අපිට පේනවා හතළිස් අට තුනෙන් බෙදූ විට පිළිතුර දාසයක් සහ ඉතුරු බිංදුවක් ලෙස ලැබෙනවා.",932)
    # sin_text_to_speech("අපි දැන් බලමු හතරෙන් බෙදන්නේ කොහොමද කියලා. ඉහත ඉගෙන ගත් ආකාරයටම පන්සිය හැත්තෑව හතරෙන් බෙදූ විට පිළිතුර එකසිය හතලිස් දෙකයි ඉතුරු දෙකක් පහත පරිදි ලැබේ",933)
    # sin_text_to_speech("අපි දැන් බලමු දෙසිය හැට පහ, පහෙන් බෙදුවාම පිළිතුර කීයක් එනවද කියලා.ඔබට දැන් පේනවා පිළිතුර පනස්තුනක් විදිහට ලැබිලා තියෙනවා.",934)
    # sin_text_to_speech("පෙර අප ඉගෙන ගත් ආකාරයටම අසූ හතර හයෙන් බෙදූවිට පිළිතුර දහ හතරක් ලෙස ලැබෙනවා.",935)
    # sin_text_to_speech("ඕනම සංඛ්‍යාවක් හතෙන් බෙදන්නේ කොහොමද කියලා අපි දැන් බලමු. දැන් අපි බලමු හත්සිය හැත්ත දෙක හතෙන් බෙදන්න. මෙම ආකාරයට අපිට හතෙන් බෙදන්න පුළුවන්.",936)
    # sin_text_to_speech("අටසිය විසි හය අටෙන් බෙදූ විට පිළිතුර එකසිය තුනයි ඉතුරු දෙකක් පහත පරිදි ලැබෙනවා.",937)
    # sin_text_to_speech("ඕනම සංඛ්‍යාවක් නවයෙන් බෙදන්නේ කොහොමද කියල අපි දැන් බලමු. අපි දැන් බලමු නවසිය පනස් හය නවයෙන් බෙදන්න. පහත ආකාරයට අපිට නවයෙන් බෙදන්න පුළුවන්. එවිට පිළිතුර එකසිය හයයි ඉතුරු දෙකයි.",938)
    counts = Counter(Aud_results)
    counts_dict = dict(counts)
    if rd_lesson > 0:
        if len(Aud_results_2) == 0:
            counts_dict["New Result"]=0
            message="You are a bloody looser. get lost"
            images=["img2.png"]
        else:    
            counts2 = Counter(Aud_results_2)
            counts_dict2 = dict(counts2)
            print(counts_dict2)
            counts_dict["New "+"lesson"+str(rd_lesson)]=counts_dict2["lesson0"+str(rd_lesson)]
            message="You Complete your Journey"
            images=["img2.png"]
        return render_template('AudioGuide.html', results=counts_dict, message=message,images=images,lesson_id="Finished")
    else:
        lesson_no=get_min_count_string(counts_dict)
        print("Shit lesson ------------------------------------>",rd_lesson)
        rd_lesson=lesson_no
        message="Since you have minimum result for lesson "+str(lesson_no)
        img_range=[3,2,2]
        images=[]
        for img in range(img_range[lesson_no-1]):
            images.append("9"+str(lesson_no)+str(img+1)+".png")
        return render_template('AudioGuide.html', results=counts_dict, message=message,images=images,lesson_id=str(lesson_no))


if __name__ == "__main__":
    port = config.AUDIO_APP_PORT if hasattr(config, 'AUDIO_APP_PORT') else 5004
    app.run(debug=True, port=port)
