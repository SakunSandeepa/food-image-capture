import cv2
import time
import os
import requests
from datetime import datetime
import openai
from openai import OpenAI
import base64


# Optional AI label
AI_LABEL = "food"
client = OpenAI(api_key=openai_api_key)
openai.api_key = openai_api_key

photo_path = './image/'

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

def analyze_image_with_openai(photo_path):
    # Read and encode image to base64
    with open(photo_path, "rb") as f:
        img_data = base64.b64encode(f.read()).decode()

    # Send image to GPT-4o-mini (vision-capable)
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please analyze the following image."},
                    {
                        "type": "image_url",
                        "image_url": {
                            # Using base64 data uri
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    }
                ]
            }
        ]
    )
    print(response.choices[0].message.content)
    return response.choices[0].message.content

cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  # Try CAP_V4L2 or remove the backend

print("📸 Press [Enter] to capture and send image. Ctrl+C to exit.")

try:
    while True:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Failed to read from camera.")
                continue

            cv2.imshow("📷 Live Camera - Press Enter to Capture", frame)
            key = cv2.waitKey(1)
            if key == 13:  # Enter key
                time.sleep(0.5)
                break

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captured_{timestamp}_{AI_LABEL}.jpg"
        full_path = os.path.join(photo_path, filename)
        os.makedirs(photo_path, exist_ok=True)
        cv2.imwrite(full_path, frame)

        print(f"✅ Saved image: {full_path}")

        print("🔍 Analyzing image with OpenAI...")
        try:
            description = analyze_image_with_openai(full_path)
            print("🧠 Description:", description)
        except Exception as e:
            description = "⚠️ Failed to get description."
            print("❌ OpenAI error:", str(e))

        resp = send_telegram_photo(full_path, caption=f"{description}\n\nCaptured at {timestamp}")
        if resp.status_code == 200:
            print("📤 Image sent to Telegram successfully.")
        else:
            print(f"⚠️ Failed to send image. Response: {resp.text}")

except KeyboardInterrupt:
    print("\n👋 Exiting...")

finally:
    cap.release()
    cv2.destroyAllWindows()