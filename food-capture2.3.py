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

# ========== CONFIG ==========
bot_token = os.getenv("BOT_TOKEN")
ch_chat_id = os.getenv("CHAT_ID")
openai_api_key = os.getenv("OPENAI_API_KEY")

AI_LABEL = "food"
PHOTO_DIR = "./image"
COOLDOWN_SECONDS = 3
WINDOW_NAME = "📷 Live Feed - Press Enter to Capture"
IMAGE_WIDTH, IMAGE_HEIGHT = 1280, 720

# ========== LOGGING ==========
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')

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
    """Send image to OpenAI for analysis."""
    import openai  # Local import for faster load if not used
    openai.api_key = openai_api_key
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


# ========== MAIN LOGIC ==========
def main():
    os.makedirs(PHOTO_DIR, exist_ok=True)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, IMAGE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, IMAGE_HEIGHT)
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, IMAGE_WIDTH, IMAGE_HEIGHT)

    logging.info("📸 Press [Enter] to capture and send image. ESC or Ctrl+C to exit.")

    last_image_hash = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                logging.error("❌ Camera frame not available.")
                continue

            # Show resized preview
            preview_frame = cv2.resize(frame, (800, 600))
            cv2.imshow(WINDOW_NAME, preview_frame)

            key = cv2.waitKey(1)
            if key == 13:  # Enter
                logging.info("🔸 Capturing image...")
                # Ensure we get a fresh frame (flush buffer)
                for _ in range(3): cap.read()
                ret, frame = cap.read()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                timestamp1 = datetime.now().strftime("%b %-d, %Y %-I:%M:%S %p")
                filename = f"captured_{timestamp}_{AI_LABEL}.jpg"
                full_path = os.path.join(PHOTO_DIR, filename)
                cv2.imwrite(full_path, frame)
                logging.info(f"✅ Image saved: {full_path}")

                # Hash to avoid duplicate images
                current_hash = compute_image_hash(full_path)
                if current_hash == last_image_hash:
                    logging.info("⚠️ Duplicate image detected. Skipping send.")
                    os.remove(full_path)
                    continue

                last_image_hash = current_hash

                # Analyze image (optional)
                # description = analyze_image_with_openai(full_path)
                description = 'Chinese Dragon Cafe - Milagiriya'
                logging.info(f"🧠 Description: {description}")

                # Send to Telegram
                logging.info("📤 Sending image to Telegram...")
                resp = send_telegram_photo(full_path, caption=f"{description}\n\nCaptured at {timestamp1}")
                if resp.status_code == 200:
                    logging.info("✅ Image sent to Telegram.")
                else:
                    logging.error(f"❌ Telegram error: {resp.text}")

                time.sleep(COOLDOWN_SECONDS)  # Simple cooldown after capture

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