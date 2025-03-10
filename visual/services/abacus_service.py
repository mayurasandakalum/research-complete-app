import base64
import os
import cv2
import numpy as np
from ultralytics import YOLO
import tempfile
from pathlib import Path

# Initialize the model once
MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                          "models", "abacus-model", "model-files", "best-3.pt")
abacus_model = YOLO(MODEL_PATH)

def decode_base64_image(base64_string):
    """Convert base64 string to OpenCV image"""
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    
    image_bytes = base64.b64decode(base64_string)
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return image

def save_base64_image(base64_string, prefix="abacus"):
    """Save base64 image to a temporary file and return the path"""
    image = decode_base64_image(base64_string)
    
    # Create temporary file with .jpg extension
    temp_file = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".jpg", delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    # Save image to the temporary file
    cv2.imwrite(temp_path, image)
    return temp_path

def process_abacus_image(base64_image):
    """Process an abacus image and return the detected value"""
    # Save the base64 image to a file
    image_path = save_base64_image(base64_image)
    
    try:
        # Run model inference
        results = abacus_model.predict(image_path)
        detections = results[0]
        
        # Define class IDs
        BEAD_CLASS_ID = 0
        STICK_CLASS_ID = 1
        
        beads = []
        sticks = []
        
        # Extract bounding boxes for beads and sticks
        for result in detections.boxes:
            class_id = int(result.cls)
            bbox = result.xyxy.cpu().numpy()[0]
            if class_id == BEAD_CLASS_ID:
                beads.append(bbox)
            elif class_id == STICK_CLASS_ID:
                sticks.append(bbox)
        
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
        
        # Calculate total abacus value
        stick_values = {1: 10000, 2: 1000, 3: 100, 4: 10, 5: 1}
        total_value = sum(
            bead_count * stick_values.get(stick_num, 0)
            for stick_num, bead_count in stick_bead_counts.items()
        )
        
        # Create annotated image path
        base_path = Path(image_path)
        annotated_path = base_path.parent / f"annotated_{base_path.name}"
        
        # Create an annotator and draw boxes
        original_img = cv2.imread(image_path)
        from ultralytics.utils.plotting import Annotator
        annotator = Annotator(original_img, line_width=1, font_size=0.5)
        
        # Define class names
        class_names = {0: "bead", 1: "stick"}
        
        # Draw detections
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
                
            # Draw box and label
            label = f"{class_names.get(class_id, 'unknown')} {conf:.2f}"
            annotator.box_label(bbox, label, color=box_color, txt_color=txt_color)
        
        # Get and save annotated image
        annotated_img = annotator.result()
        cv2.imwrite(str(annotated_path), annotated_img)
        
        result = {
            'total_value': total_value,
            'bead_counts': list(sorted(stick_bead_counts.items())),
            'original_path': image_path,
            'annotated_path': str(annotated_path)
        }
        return result
    
    finally:
        # In a production environment, you might want to clean up temporary files
        # os.unlink(image_path)
        pass

def check_abacus_answer(base64_image, expected_answer):
    """
    Check if the abacus image shows the expected answer
    Returns a tuple: (is_correct, detected_value, annotated_image_path)
    """
    try:
        # Convert expected_answer to int for comparison
        expected_value = int(expected_answer)
        
        # Process the image
        result = process_abacus_image(base64_image)
        detected_value = result['total_value']
        annotated_path = result['annotated_path']
        
        # Check if the detected value matches the expected value
        is_correct = (detected_value == expected_value)
        
        return is_correct, detected_value, annotated_path
    
    except Exception as e:
        # Log the error and return False
        print(f"Error checking abacus answer: {str(e)}")
        return False, None, None
