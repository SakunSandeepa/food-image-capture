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
import threading
from dotenv import load_dotenv
from playsound import playsound

load_dotenv()

# ========== CONFIG ==========
bot_token = os.getenv("BOT_TOKEN")
ch_chat_id = os.getenv("CHAT_ID")
openai_api_key = os.getenv("OPENAI_API_KEY")

AI_LABEL = "food"
PHOTO_DIR = "./image"
COOLDOWN_SECONDS = 2
WINDOW_NAME = "📷 Live Feed - Press Enter to Capture"
IMAGE_WIDTH, IMAGE_HEIGHT = 1280, 720

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO, 
    format='[%(asctime)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('capture_log.txt', mode='a')
    ]
)

# ========== UTILITY FUNCTIONS ==========
def compute_image_hash(image_path):
    """Return a SHA256 hash of the image contents."""
    with open(image_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def send_telegram_photo(photo_path, caption="Food Image Capture"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    with open(photo_path, 'rb') as photo:
        response = requests.post(
            url,
            data={'chat_id': ch_chat_id, 'caption': caption},
            files={'photo': photo}
        )
    return response

def analyze_image_with_openai(photo_path):
    openai.api_key = openai_api_key
    with open(photo_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()

    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text":
"""You are a food inspector AI. Briefly analyze this food photo and reply in this format:

Summary: [one short line]
Color: [one word or phrase]
Shape/Size: [one word or phrase]
Packaging: [short phrase or 'N/A']
Presentation: [short phrase]
Unusual: [short phrase or 'None']
Rating: [bad|normal|good|excellent] [emoji: 🔴🟠🟢🔵]

Keep it concise and use the emoji for the rating at the end.
""" 
                        },
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

def draw_code_box(frame, code_text):
    """Overlay the current Order Number on the frame."""
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (500, 60), (0, 0, 0), -1)  # background box
    cv2.putText(overlay, f"Order Number: {code_text}", (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
    alpha = 0.6
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
    return frame

def analyze_and_send(photo_path, caption_parts):
    # Run in background: Analyze food quality, then send to Telegram
    logging.info("🔍 Analyzing food quality with OpenAI...")
    quality_result = analyze_image_with_openai(photo_path)
    logging.info(f"🧠 Food quality result: {quality_result}")
    caption_parts.append(f"\nAI Food Quality:\n{quality_result}")
    caption = "\n".join(caption_parts)
    resp = send_telegram_photo(photo_path, caption=caption)
    if resp.status_code == 200:
        logging.info("✅ Image sent to Telegram.")
    else:
        logging.error(f"❌ Telegram error: {resp.text}")

def play_success_sound():
    playsound('success.wav', block=False)


# ========== MAIN FUNCTION ==========
def main():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMAGE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMAGE_HEIGHT)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, IMAGE_WIDTH, IMAGE_HEIGHT)

    logging.info("📸 Type Order Number, [Enter]=Capture, [ESC]=Exit.")

    last_image_hash = None
    code_text = ""

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                logging.error("❌ Camera frame not available.")
                continue

            display_frame = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT))
            display_frame = draw_code_box(display_frame, code_text)
            cv2.imshow(WINDOW_NAME, display_frame)

            key = cv2.waitKey(1) & 0xFF

            # Handle alphanumeric input and backspace
            if 32 <= key <= 126:  # Printable characters
                code_text += chr(key)
            elif key == 8:  # Backspace
                code_text = code_text[:-1]
            elif key == 13:  # Enter
                item_code = code_text.strip()
                logging.info(f"🔸 Capturing image with code: {item_code}")
                for _ in range(2): cap.read()
                ret, frame = cap.read()
                timestamp = datetime.now().strftime("%b %-d, %Y %-I:%M:%S %p")
                safe_code = item_code.replace(" ", "_") if item_code else ""
                filename = (f"captured_{timestamp.replace(':', '-')}_{safe_code}_{AI_LABEL}.jpg"
                            if item_code else
                            f"captured_{timestamp.replace(':', '-')}_{AI_LABEL}.jpg")
                full_path = os.path.join(PHOTO_DIR, filename)
                cv2.imwrite(full_path, frame)
                logging.info(f"✅ Image saved: {full_path}")
                play_success_sound()

                current_hash = compute_image_hash(full_path)
                if current_hash == last_image_hash:
                    logging.info("⚠️ Duplicate image detected. Skipping send.")
                    os.remove(full_path)
                    code_text = ""
                    continue
                last_image_hash = current_hash

                description = 'Chinese Dragon Cafe - Milagiriya Branch'
                caption_parts = []
                if item_code:
                    caption_parts.append(f"Order Number: {item_code}")
                caption_parts.append(description)
                caption_parts.append(f"Captured at {timestamp}")

                # Launch AI analysis and Telegram sending in background
                threading.Thread(
                    target=analyze_and_send,
                    args=(full_path, caption_parts),
                    daemon=True
                ).start()
                logging.info("📤 AI analysis and Telegram upload started in background.")

                code_text = ""
                time.sleep(COOLDOWN_SECONDS)

            elif key == 27:  # ESC
                logging.info("👋 Exiting...")
                break

    except KeyboardInterrupt:
        logging.info("👋 Exiting...")

    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()