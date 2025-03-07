import pyautogui
from dotenv import load_dotenv
import os
import time
from AppOpener import open
import base64
from io import BytesIO
from PIL import Image
from groq import Groq
from semi import openlmsnow

load_dotenv()

class GroqImageComparisonAgent:
    def __init__(self):
        self.password = os.environ.get('PASSWORD')
        self.groq_api_key = os.environ.get('GROQ_API_KEY')
        
        if not self.password:
            print("Error: PASSWORD environment variable not set.")
            return
        if not self.groq_api_key:
            print("Error: GROQ_API_KEY environment variable not set.")
            return
        
        # Initialize Groq client
        self.client = Groq(api_key=self.groq_api_key)
        self.lms_opener = openlmsnow()
        
        # Reference images paths (you need to create these screenshots)
        self.reference_images = {
            "openlms": self.load_reference_image(r"reference_images\\openlms.png")
        }
        
        # Open the app immediately
        self.lms_opener.openapp()
        time.sleep(5)  # Wait for the app to launch
        
        # Run the openLMS function repeatedly until the screen matches
        self.ensure_openlms()

    def load_reference_image(self, filepath):
        """Load and convert reference image to base64"""
        try:
            with open(filepath, "rb") as image_file:
                img_data = base64.b64encode(image_file.read()).decode('utf-8')
            return img_data
        except FileNotFoundError:
            print(f"Error: Reference image not found at {filepath}")
            return None

    def capture_screenshot(self):
        """Capture screenshot and convert to base64"""
        screenshot = pyautogui.screenshot()
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str

    def compare_with_groq(self, screenshot_base64, reference_base64):
        """Compare screenshot with reference image using Groq API"""
        if reference_base64 is None:
            return False
        
        prompt = """
        Compare these two images:
        1. The current screenshot
        2. A reference image for the 'openlms' action
        Determine if they match (are visually similar enough to indicate the same screen state).
        Return a JSON object with a single key 'is_match' set to true or false.
        """

        response = self.client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{reference_base64}"}}
                    ]
                }
            ],
            max_tokens=100,
            temperature=0.5,
            response_format={"type": "json_object"}
        )

        result = eval(response.choices[0].message.content)  # Use json.loads in production
        return result["is_match"]

    def ensure_openlms(self):
        """Keep running openLMS until the screen matches the reference image"""
        while True:
            try:
                screenshot_base64 = self.capture_screenshot()
                if self.compare_with_groq(screenshot_base64, self.reference_images["openlms"]):
                    print("LMS successfully opened. Exiting loop.")
                    break
                print("LMS not detected, retrying...")
                self.lms_opener.openlms()
                time.sleep(5)  # Wait before checking again
            except Exception as e:
                print(f"Error in LMS verification loop: {e}")
                time.sleep(5)  # Retry after delay


def main():
    GroqImageComparisonAgent()

if __name__ == "__main__":
    main()
