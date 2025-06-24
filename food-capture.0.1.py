import cv2
import time
from datetime import datetime

# Optional: your own label or placeholder for AI-detected class
AI_LABEL = "food"  # You could replace this with an actual AI-detected label later

# Open the webcam
cap = cv2.VideoCapture("/dev/video0")

if not cap.isOpened():
    raise IOError("Cannot open /dev/video0")

print("📸 Press [Enter] to capture image. Press Ctrl+C to exit.")

try:
    while True:
        input()  # Wait for Enter
        time.sleep(0.5)

        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to capture image.")
            continue

        # Create a timestamped and labeled filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_{timestamp}_{AI_LABEL}.jpg"

        # Save the image
        cv2.imwrite(filename, frame)
        print(f"✅ Saved image: {filename}")

except KeyboardInterrupt:
    print("\n👋 Exiting...")

finally:
    cap.release()
