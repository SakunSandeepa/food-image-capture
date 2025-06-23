import cv2
import time
import os
import requests
from datetime import datetime
import openai
from openai import OpenAI
import base64
import hashlib
import logging

AI_LABEL = "food"
PHOTO_DIR = "./image"
COOLDOWN_SECONDS = 3

client = OpenAI(api_key=openai_api_key)
openai.api_key = openai_api_key

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

last_image_hash = None
last_capture_time = 0

# === FUNCTIONS ===

def compute_image_hash(image_path):
    """Return a SHA256 hash of the image contents."""
    with open(image_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def send_telegram_photo(photo_path, caption="Food Image Capture"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        response = requests.post(
            url,
            data={'chat_id': chat_id, 'caption': caption},
            files={'photo': photo}
        )
    return response


def analyze_image_with_openai(photo_path):
    """Send image to OpenAI for analysis."""
    with open(photo_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Please analyze the following image."},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }}
                    ]
                }
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.warning(f"OpenAI analysis failed: {e}")
        return "Food image"

# === MAIN LOOP ===

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

os.makedirs(PHOTO_DIR, exist_ok=True)

cv2.namedWindow("📷 Live Feed - Press Enter to Capture", cv2.WINDOW_NORMAL)
cv2.resizeWindow("📷 Live Feed - Press Enter to Capture", 1280, 720)

# cv2.namedWindow("📷 Live Feed", cv2.WND_PROP_FULLSCREEN)
# cv2.setWindowProperty("📷 Live Feed", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)


logging.info("📸 Press [Enter] to capture and send image. Ctrl+C to exit.")

def get_fresh_frame(cap, attempts=5, delay=0.1):
    for _ in range(attempts):
        ret, frame = cap.read()
        time.sleep(delay)
    return ret, frame


try:
    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            logging.error("❌ Camera frame not available.")
            continue

        resized_frame = cv2.resize(frame, (800, 600))
        cv2.imshow("📷 Live Feed - Press Enter to Capture", resized_frame)

        key = cv2.waitKey(1)

        if key == 13:  # Enter key
            logging.info("🔸 Capturing image...")
            # Optional: flush old frames
            for _ in range(5):
                cap.read()
                time.sleep(0.1)
            ret, frame = cap.read()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"captured_{timestamp}_{AI_LABEL}.jpg"
            full_path = os.path.join(PHOTO_DIR, filename)
            cv2.imwrite(full_path, frame)
            logging.info(f"✅ Image saved: {full_path}")

            current_hash = compute_image_hash(full_path)
            # global last_image_hash
            if current_hash == last_image_hash:
                logging.info("⚠️ Duplicate image detected. Skipping send.")
                os.remove(full_path)
                continue

            last_image_hash = current_hash

            logging.info("🔍 Analyzing image with OpenAI...")
            # description = analyze_image_with_openai(full_path)
            description = 'Chinese Dragon Cafe'
            logging.info(f"🧠 Description: {description}")

            logging.info("📤 Sending image to Telegram...")
            resp = send_telegram_photo(full_path, caption=f"{description}\n\nCaptured at {timestamp}")
            if resp.status_code == 200:
                logging.info("✅ Image sent to Telegram.")
            else:
                logging.error(f"❌ Telegram error: {resp.text}")

        elif key == 27:  # ESC key to exit
            logging.info("👋 Exiting...")
            break

except KeyboardInterrupt:
    logging.info("👋 Exiting...")

finally:
    cap.release()
    cv2.destroyAllWindows()

# def send_telegram_photo(photo_path, caption="Food Image Capture"):
#     url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
#     with open(photo_path, 'rb') as photo:
#         data = {
#             'chat_id': chat_id,
#             'caption': caption
#         }
#         files = {
#             'photo': photo
#         }
#         response = requests.post(url, data=data, files=files)
#     return response
#
#
# def analyze_image_with_openai(photo_path):
#     # Read and encode image to base64
#     with open(photo_path, "rb") as f:
#         img_data = base64.b64encode(f.read()).decode()
#
#     # Send image to GPT-4o-mini (vision-capable)
#     response = openai.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[
#             {
#                 "role": "user",
#                 "content": [
#                     {"type": "text", "text": "Please analyze the following image."},
#                     {
#                         "type": "image_url",
#                         "image_url": {
#                             # Using base64 data uri
#                             "url": f"data:image/jpeg;base64,{img_data}"
#                         }
#                     }
#                 ]
#             }
#         ]
#     )
#     print(response.choices[0].message.content)
#     return response.choices[0].message.content
#
#
# print("📸 Press [Enter] to capture and send image. Ctrl+C to exit.")
#
# cap = cv2.VideoCapture(0)  # try index 0 or 1 instead of /dev/video0
#
# try:
#     while True:
#         input()
#         time.sleep(0.5)
#
#         ret, frame = cap.read()
#         if not ret:
#             print("❌ Failed to capture image.")
#             continue
#
#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#         filename = f"captured_{timestamp}_{AI_LABEL}.jpg"
#         full_path = os.path.join(photo_path, filename)
#         os.makedirs(photo_path, exist_ok=True)
#         cv2.imwrite(full_path, frame)
#
#         print(f"✅ Saved image: {full_path}")
#
#         print("🔍 Analyzing image with OpenAI...")
#         try:
#             # description = analyze_image_with_openai(full_path)
#             description = 'Food capture'
#             print("🧠 Description:", description)
#         except Exception as e:
#             description = "⚠️ Failed to get description."
#             print("❌ OpenAI error:", str(e))
#
#         resp = send_telegram_photo(full_path, caption=f"{description}\n\nCaptured at {timestamp}")
#         if resp.status_code == 200:
#             print("📤 Image sent to Telegram successfully.")
#         else:
#             print(f"⚠️ Failed to send image. Response: {resp.text}")
#
# except KeyboardInterrupt:
#     print("\n👋 Exiting...")
#
# finally:
#     cap.release()
