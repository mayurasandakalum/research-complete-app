import base64
import os
import cv2
import numpy as np
import torch
import einops
import torch.nn as nn
import torchvision.models as models
import tempfile
from pathlib import Path
import time
import re
from datetime import datetime

# Use GPU if available, otherwise fall back to CPU
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device} for clock detection model")

# Define the models
model_stn = models.resnet50(pretrained=False)
model_stn.fc = nn.Linear(2048, 8)
model = models.resnet50(pretrained=False)
model.fc = nn.Linear(2048, 720)

# Get the absolute path to the model files
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
model_stn_path = os.path.join(project_root, "models", "clock-model", "model-files", "model_stn.pth")
model_path = os.path.join(project_root, "models", "clock-model", "model-files", "model.pth")

# Load the saved model weights
model_stn.load_state_dict(torch.load(model_stn_path, map_location=device))
model.load_state_dict(torch.load(model_path, map_location=device))

model_stn.to(device)
model.to(device)
model_stn.eval()
model.eval()

# Define warp function (from original clock_app.py)
def warp(img, M):
    grid = nn.functional.affine_grid(M[:, :2], img.size(), align_corners=False)
    img_warped = nn.functional.grid_sample(img, grid, align_corners=False)
    return img_warped

def decode_base64_image(base64_string):
    """Convert base64 string to OpenCV image"""
    if "base64," in base64_string:
        base64_string = base64_string.split("base64,")[1]
    
    image_bytes = base64.b64decode(base64_string)
    np_array = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
    return image

def save_base64_image(base64_string, prefix="clock"):
    """Save base64 image to a temporary file and return the path"""
    image = decode_base64_image(base64_string)
    
    # Create temporary file with .jpg extension
    temp_file = tempfile.NamedTemporaryFile(prefix=prefix, suffix=".jpg", delete=False)
    temp_path = temp_file.name
    temp_file.close()
    
    # Save image to the temporary file
    cv2.imwrite(temp_path, image)
    return temp_path

def process_clock_image(image_path):
    """Process a clock image and return the detected time"""
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
        pred_st = torch.cat([pred_st, torch.ones(1, 1).to(device)], 1)
        Minv_pred = torch.reshape(pred_st, (-1, 3, 3))
        img_ = warp(img, Minv_pred)

        # Main Model Prediction
        pred = model(img_)

        # Get top prediction
        max_pred = torch.argmax(pred, dim=1)
        max_h = max_pred[0] // 60
        max_m = max_pred[0] % 60

        # Format the time prediction
        time_prediction = f"{int(max_h):02d}:{int(max_m):02d}"

    # Create annotated image with prediction
    original_img = cv2.imread(image_path)
    
    # Draw predicted time on the image
    cv2.putText(
        original_img,
        f"Detected: {time_prediction}",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2,
    )
    
    # Save annotated image
    base_path = Path(image_path)
    annotated_path = base_path.parent / f"annotated_{base_path.name}"
    cv2.imwrite(str(annotated_path), original_img)
    
    result = {
        'detected_time': time_prediction,
        'hours': int(max_h),
        'minutes': int(max_m),
        'original_path': image_path,
        'annotated_path': str(annotated_path)
    }
    
    return result

def check_clock_answer(base64_image, expected_answer):
    """
    Check if the clock image shows the expected time
    Returns a tuple: (is_correct, detected_value, annotated_image_path)
    
    A tolerance of ±3 minutes is allowed for correct answers.
    """
    try:
        # Save the base64 image to a file
        image_path = save_base64_image(base64_image)
        
        # Process the image
        result = process_clock_image(image_path)
        detected_time = result['detected_time']
        annotated_path = result['annotated_path']
        
        # Parse expected answer and format for comparison
        expected_minutes_total = 0
        detected_minutes_total = 0
        
        # Parse expected time
        if ":" in expected_answer:
            parts = expected_answer.split(":")
            if len(parts) == 2:
                expected_hour = int(parts[0])
                expected_minute = int(parts[1])
                expected_formatted = f"{expected_hour:02d}:{expected_minute:02d}"
                expected_minutes_total = expected_hour * 60 + expected_minute
            else:
                expected_formatted = expected_answer
        else:
            # If no colon, try to parse as a number of minutes
            try:
                expected_minutes_total = int(expected_answer)
                expected_hour = expected_minutes_total // 60
                expected_minute = expected_minutes_total % 60
                expected_formatted = f"{expected_hour:02d}:{expected_minute:02d}"
            except ValueError:
                expected_formatted = expected_answer
        
        # Parse detected time
        if ":" in detected_time:
            parts = detected_time.split(":")
            if len(parts) == 2:
                detected_hour = int(parts[0])
                detected_minute = int(parts[1])
                detected_minutes_total = detected_hour * 60 + detected_minute
        
        # Check if the detected time is within ±3 minutes of the expected time
        # First, check if we have valid times to compare
        if expected_minutes_total > 0 and detected_minutes_total > 0:
            # Calculate the difference in minutes
            time_difference = abs(detected_minutes_total - expected_minutes_total)
            
            # Handle edge cases around 12 hours / 24 hours
            if time_difference > 12 * 60 - 3:  # If we're near the day boundary
                time_difference = 24 * 60 - time_difference
            
            # Check if within tolerance of 3 minutes
            is_correct = (time_difference <= 3)
            
            # Add tolerance information to the annotated image
            if os.path.exists(annotated_path):
                original_img = cv2.imread(annotated_path)
                if time_difference <= 3:
                    status_text = f"Within tolerance: {time_difference} min diff (±3 min allowed)"
                    color = (0, 255, 0)  # Green for correct
                else:
                    status_text = f"Outside tolerance: {time_difference} min diff (±3 min allowed)"
                    color = (0, 0, 255)  # Red for incorrect
                
                cv2.putText(
                    original_img,
                    status_text,
                    (10, 60),  # Position below the detected time
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )
                cv2.imwrite(str(annotated_path), original_img)
        else:
            # If we couldn't parse the times properly, fall back to exact string comparison
            is_correct = (detected_time == expected_formatted)
        
        return is_correct, detected_time, annotated_path
    
    except Exception as e:
        # Log the error and return False
        print(f"Error checking clock answer: {str(e)}")
        return False, None, None

def check_clock_answer(base64_image, correct_answer):
    """
    Check if the clock image matches the expected time answer
    
    Args:
        base64_image (str): Base64-encoded image of the clock
        correct_answer (str): Expected time in format like "3:45" or "15:30"
    
    Returns:
        tuple: (is_correct, detected_time, annotated_image_path)
    """
    try:
        # Convert base64 to image
        image_data = base64.b64decode(base64_image.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Create a copy for annotation
        annotated_image = image.copy()
        
        # Preprocess image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Simple placeholder implementation - in a real system, this would use 
        # computer vision algorithms to detect clock hands or digital time
        # For this example, we'll just compare to the expected answer
        
        # Expected time - parse from correct_answer format (HH:MM)
        try:
            # Parse time using regex to handle both 12-hour and 24-hour formats
            match = re.match(r'(\d{1,2}):(\d{2})', correct_answer)
            if match:
                expected_hour = int(match.group(1))
                expected_minute = int(match.group(2))
            else:
                # Default if format doesn't match
                expected_hour = 0
                expected_minute = 0
                
            # For this demonstration, we'll randomly decide if it's correct
            # In a real implementation, this would be based on actual CV detection
            import random
            is_correct = random.choice([True, False])
            
            # Generate a detected time that's either correct or slightly off
            if is_correct:
                detected_hour = expected_hour
                detected_minute = expected_minute
            else:
                # Generate a random time that's off by a small amount
                detected_hour = expected_hour + random.choice([-1, 0, 1])
                detected_minute = expected_minute + random.choice([-5, 5])
                
                # Fix hour/minute boundaries
                if detected_minute < 0:
                    detected_minute += 60
                    detected_hour -= 1
                elif detected_minute >= 60:
                    detected_minute -= 60
                    detected_hour += 1
                
                if detected_hour < 0:
                    detected_hour += 12
                elif detected_hour >= 24:
                    detected_hour %= 24
            
            # Format detected time
            detected_time = f"{detected_hour}:{detected_minute:02d}"
            
            # Add text to annotated image
            cv2.putText(
                annotated_image,
                f"Detected: {detected_time}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0) if is_correct else (0, 0, 255),
                2,
            )
            
            # Save annotated image
            timestamp = int(time.time())
            output_dir = "temp_images"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"clock_{timestamp}.jpg")
            cv2.imwrite(output_path, annotated_image)
            
            return is_correct, detected_time, output_path
            
        except Exception as e:
            print(f"Error parsing time: {str(e)}")
            return False, "Error", None
            
    except Exception as e:
        print(f"Error processing clock image: {str(e)}")
        return False, "Error", None
