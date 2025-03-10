import time
from ultralytics import YOLO


def run_inference(model, image_path):
    """Run model inference on image and measure time"""
    start_time = time.time()
    results = model.predict(image_path)
    inference_time = (time.time() - start_time) * 1000  # Convert to ms
    return results, inference_time


def count_detections(results):
    """Count beads and sticks in detection results"""
    detections = results[0]

    # Assuming class IDs as in the original code
    BEAD_CLASS_ID = 0
    STICK_CLASS_ID = 1

    bead_count = 0
    stick_count = 0

    for result in detections.boxes:
        class_id = int(result.cls)
        if class_id == BEAD_CLASS_ID:
            bead_count += 1
        elif class_id == STICK_CLASS_ID:
            stick_count += 1

    return bead_count, stick_count
