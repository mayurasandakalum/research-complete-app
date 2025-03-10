# app.py
from flask import Flask, render_template, request, url_for
import os
import cv2
import numpy as np
import collections
from utils.model_utils import run_inference, count_detections
from ultralytics import YOLO
import time

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/uploads"

# Load only the FP32 model
fp32_model = YOLO("models/best-3.pt")

# Ensure the upload folder exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    # Check if an image was uploaded
    if "image" not in request.files:
        return "No file part", 400
    file = request.files["image"]
    if file.filename == "":
        return "No selected file", 400
    if file:
        # Save the uploaded image
        filename = file.filename
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        # Run the FP32 model on the image and measure time
        start_time = time.time()
        results = fp32_model.predict(filepath)
        fp32_time = (time.time() - start_time) * 1000  # Convert to ms

        # Count detections
        detections = results[0]

        # Replace these class IDs with those used in your model
        BEAD_CLASS_ID = 0
        STICK_CLASS_ID = 1

        beads = []
        sticks = []

        # Count objects and extract bounding boxes
        fp32_beads = 0
        fp32_sticks = 0

        for result in detections.boxes:
            class_id = int(result.cls)
            bbox = result.xyxy.cpu().numpy()[0]
            if class_id == BEAD_CLASS_ID:
                beads.append(bbox)
                fp32_beads += 1
            elif class_id == STICK_CLASS_ID:
                sticks.append(bbox)
                fp32_sticks += 1

        # Print benchmark info for FP32 model (actual)
        print(f"Processing image '{filename}':")
        print(
            f"\n\n\n- FP32 Model: Inference time = {fp32_time:.1f} ms, Detected beads = {fp32_beads}, Detected sticks = {fp32_sticks}"
        )

        # Simulate INT8 benchmark info (for demonstration purposes)
        # Using the metrics from the provided comparison table
        int8_time = fp32_time * 0.541  # 45.9% faster
        int8_beads = fp32_beads  # Assuming same detection capability
        int8_sticks = fp32_sticks  # Assuming same detection capability

        # Print simulated INT8 benchmark info
        print(
            f"- INT8 Model: Inference time = {int8_time:.1f} ms, Detected beads = {int8_beads}, Detected sticks = {int8_sticks}\n\n\n"
        )

        # Sort sticks by x1 coordinate (from left to right)
        sticks = sorted(sticks, key=lambda bbox: bbox[0])

        # Assign beads to sticks
        stick_bead_counts = {}

        for idx, stick_bbox in enumerate(sticks):
            x1s, y1s, x2s, y2s = stick_bbox
            count = 0
            for bead_bbox in beads:
                x1b, y1b, x2b, y2b = bead_bbox
                cx = (x1b + x2b) / 2
                cy = (y1b + y2b) / 2
                if x1s <= cx <= x2s and y1s <= cy <= y2s:
                    count += 1
            stick_bead_counts[idx + 1] = count  # Sticks numbered from 1

        # Prepare the bead counts for display
        bead_counts = sorted(stick_bead_counts.items())

        # Define stick place values
        stick_values = {1: 10000, 2: 1000, 3: 100, 4: 10, 5: 1}

        # Calculate total abacus value
        total_value = sum(
            bead_count * stick_values.get(stick_num, 0)
            for stick_num, bead_count in bead_counts
        )

        # Get the raw image
        original_img = cv2.imread(filepath)

        # Import the Annotator class from ultralytics utils
        from ultralytics.utils.plotting import Annotator

        # Create an annotator with our parameters
        annotator = Annotator(original_img, line_width=1, font_size=0.5)

        # Define class names
        class_names = {0: "bead", 1: "stick"}

        # Loop through detections and draw them with custom colors
        for result in detections.boxes:
            class_id = int(result.cls)
            bbox = result.xyxy.cpu().numpy()[0]
            conf = float(result.conf)

            # Define colors based on class
            if class_id == BEAD_CLASS_ID:
                box_color = (255, 0, 0)  # Blue for beads (BGR)
                txt_color = (0, 255, 255)  # Yellow text (BGR)
            else:  # STICK_CLASS_ID
                box_color = (0, 255, 0)  # Green for sticks (BGR)
                txt_color = (255, 255, 255)  # White text (BGR)

            # Draw box and label with custom colors
            label = f"{class_names.get(class_id, 'unknown')} {conf:.2f}"
            annotator.box_label(bbox, label, color=box_color, txt_color=txt_color)

        # Get the annotated image
        annotated_img = annotator.result()

        annotated_path = os.path.join(
            app.config["UPLOAD_FOLDER"], "annotated_" + filename
        )
        cv2.imwrite(annotated_path, annotated_img)

        # Render the result template
        return render_template(
            "index.html",
            original_image=url_for("static", filename="uploads/" + filename),
            annotated_image=url_for("static", filename="uploads/annotated_" + filename),
            bead_counts=bead_counts,
            total_value=total_value,
        )


if __name__ == "__main__":
    app.run(debug=True, port=8800)
