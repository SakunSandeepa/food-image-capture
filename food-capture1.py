import cv2
import time
import os
import requests
from datetime import datetime
import openai


def send_telegram_photo(photo_path, caption="Food Image Capture"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        data = {
            'chat_id': chat_id,
            'caption': caption
        }
        files = {
            'photo': photo
        }
        response = requests.post(url, data=data, files=files)
    return response

# Optional AI label
AI_LABEL = "food"

# Open webcam
cap = cv2.VideoCapture("/dev/video0")

if not cap.isOpened():
    raise IOError("Cannot open /dev/video0")

print("📸 Press [Enter] to capture and send image. Ctrl+C to exit.")

try:
    while True:
        input()  # Wait for Enter key
        time.sleep(0.5)

        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to capture image.")
            continue

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_{timestamp}_{AI_LABEL}.jpg"
        cv2.imwrite(filename, frame)

        print(f"✅ Saved image: {filename}")
        resp = send_telegram_photo(filename, caption=f"Milagiriya Food Captured")
        if resp.status_code == 200:
            print("📤 Image sent to Telegram successfully.")
        else:
            print(f"⚠️ Failed to send image. Response: {resp.text}")

except KeyboardInterrupt:
    print("\n👋 Exiting...")

finally:
    cap.release()