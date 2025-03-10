# app.py
import os
import torch
import einops
import numpy as np
import torch.nn as nn
import torchvision.models as models
from natsort import natsorted
from flask import Flask, request, render_template, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import cv2
import base64
import time  # Add this import

# Initialize the Flask application
app = Flask(__name__)

# Set up the upload folder
app.config["UPLOAD_FOLDER"] = "static/uploads"
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Allowed extensions for file upload
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


# Check for allowed file extensions
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# Load your trained models
device = "cpu"

# Define the models
model_stn = models.resnet50(pretrained=False)
model_stn.fc = nn.Linear(2048, 8)
model = models.resnet50(pretrained=False)
model.fc = nn.Linear(2048, 720)

# Load the saved model weights
model_stn_path = "models/model_stn.pth"  # Update with your actual path
model_path = "models/model.pth"  # Update with your actual path

model_stn.load_state_dict(torch.load(model_stn_path, map_location=device))
model.load_state_dict(torch.load(model_path, map_location=device))

model_stn.to(device)
model.to(device)
model_stn.eval()
model.eval()


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/upload_image", methods=["POST"])
def upload_image():
    try:
        filename = None
        file_path = None

        # Handle webcam capture
        captured_image_data = request.form.get("captured_image")
        if captured_image_data:
            # Decode the base64 image data
            image_data = captured_image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)
            filename = "captured_image.png"
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            # Save the image to disk
            with open(file_path, "wb") as f:
                f.write(image_bytes)

        # Handle file upload
        elif "file" in request.files:
            file = request.files["file"]
            if file.filename == "":
                return render_template("index.html", error="No file selected")
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                file.save(file_path)
            else:
                return render_template("index.html", error="Invalid file type")
        else:
            return render_template("index.html", error="No image provided")

        # Process image and get prediction
        time_prediction = predict_time(file_path)

        return render_template(
            "index.html",
            show_result=True,
            image_url=url_for("static", filename=f"uploads/{filename}"),
            time_prediction=time_prediction,
        )

    except Exception as e:
        return render_template("index.html", error=str(e))


def predict_time(image_path):
    # Start timing
    start_time = time.time()

    # Load and preprocess the image
    img = cv2.imread(image_path)
    img = cv2.resize(img, (224, 224)) / 255.0
    img = einops.rearrange(img, "h w c -> c h w")
    img = torch.Tensor(img)
    img = img.float().to(device)
    img = torch.unsqueeze(img, 0)

    with torch.no_grad():
        # STN Model Prediction
        pred_st = model_stn(img)
        print("pred_st: ", pred_st)
        pred_st = torch.cat([pred_st, torch.ones(1, 1).to(device)], 1)
        print("pred_st-concat: ", pred_st)
        Minv_pred = torch.reshape(pred_st, (-1, 3, 3))
        img_ = warp(img, Minv_pred)

        # Main Model Prediction
        pred = model(img_)

        # Get top prediction
        max_pred = torch.argmax(pred, dim=1)
        print("max_pred: ", max_pred)
        max_h = max_pred[0] // 60
        max_m = max_pred[0] % 60

        # Format the time prediction
        time_prediction = f"{int(max_h):02d}:{int(max_m):02d}"

    # Calculate and print inference time
    inference_time = time.time() - start_time
    print(f"Inference time: {inference_time:.3f} seconds")

    return time_prediction


# The warp function
def warp(img, M):
    grid = nn.functional.affine_grid(M[:, :2], img.size(), align_corners=False)
    img_warped = nn.functional.grid_sample(img, grid, align_corners=False)
    return img_warped


if __name__ == "__main__":
    app.run(debug=True)
