import pyautogui
from dotenv import load_dotenv
import os
import time
import subprocess
import base64
from io import BytesIO
from PIL import Image
from openai import OpenAI
import json

load_dotenv()

class LMSAutomator:
    def __init__(self):
        self.password = os.environ.get('PASSWORD')
        self.user_id = os.environ.get('USER_ID')
        self.openrouter_api_key = os.environ.get('OPENROUTER_API_KEY')
        self.max_login_attempts = 3
        
        if not self.password:
            print("Error: PASSWORD environment variable not set.")
            return
        if not self.user_id:
            print("Error: USER_ID environment variable not set.")
            return
        if not self.openrouter_api_key:
            print("Error: OPENROUTER_API_KEY environment variable not set.")
            return
        
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.openrouter_api_key,
        )
        
        self.flow_steps = [
            {"name": "profile_selected", "function": self.openprofilecoord, "image_path": "lmsopen/reference_images/profile_selected.png"},
            {"name": "lms_open", "function": self.openlms, "image_path": "lmsopen/reference_images/lms_open.png"},
            {"name": "password_screen", "function": lambda: self.inputpassword(self.password), "image_path": "lmsopen/reference_images/password_screen.png"},
            {"name": "logged_in", "function": None, "image_path": "lmsopen/reference_images/logged_in.png"}
        ]
        
        os.makedirs(r"lmsopen\\reference_images", exist_ok=True)
        
        self.reference_images = {}
        for step in self.flow_steps:
            image_path = step["image_path"]
            absolute_path = os.path.abspath(image_path)
            if os.path.exists(absolute_path):
                try:
                    with open(absolute_path, "rb") as image_file:
                        if image_file is None:
                            print(f"CRITICAL: open({absolute_path}, 'rb') returned None")
                            self.reference_images[step["name"]] = None
                            continue
                        img_data = base64.b64encode(image_file.read()).decode('utf-8')
                        self.reference_images[step["name"]] = img_data
                except Exception as e:
                    print(f"Error loading reference image {absolute_path}: {e}")
                    self.reference_images[step["name"]] = None
            else:
                print(f"Reference image not found: {absolute_path}")
                self.reference_images[step["name"]] = None
        
        self.smart_execute_flow()

    def capture_screenshot(self):
        screenshot = pyautogui.screenshot()
        buffered = BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        return img_str

    def compare_with_openrouter(self, screenshot_base64, reference_base64, step_name):
        if reference_base64 is None:
            print(f"Skipping comparison for {step_name} - no reference image")
            return False

        prompt = f"""
        Analyze this screenshot and describe its key UI elements in detail.
        This is part of an LMS login process, and I want to determine if it matches the '{step_name}' step.
        Return ONLY a single JSON object with:
        - 'description': A textual description of the screenshot's UI elements.
        - 'is_match': A boolean indicating if this screenshot likely represents the '{step_name}' step.
        - 'is_browser': A boolean indicating if this screenshot shows a browser window.
        - 'is_login_error': A boolean indicating if this shows a login error message.
        For example:
        - 'profile_selected': Expect a profile selection screen with user avatars or names.
        - 'lms_open': Expect the LMS homepage or login page.
        - 'password_screen': Expect a password input field.
        - 'logged_in': Expect a dashboard or logged-in LMS interface.
        Focus on key elements that define the step, ignoring minor differences.
        Do not include any text outside the JSON object.
        Example response: {{"description": "Screen showing a profile selection interface with user avatars and names, an 'Add' button, and a 'Guest mode' option.", "is_match": true, "is_browser": true, "is_login_error": false}}
        """

        try:
            response = self.client.chat.completions.create(
                model="qwen/qwen2.5-vl-72b-instruct:free",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{screenshot_base64}"}},
                        ]
                    }
                ],
                max_tokens=200,
                temperature=0.5,
                response_format={"type": "json_object"},
                extra_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "LMS Automator",
                }
            )

            raw_content = response.choices[0].message.content
            print(f"Raw response for {step_name}: {raw_content}")

            try:
                json_start = raw_content.find('{')
                json_end = raw_content.rfind('}') + 1
                json_str = raw_content[json_start:json_end]
                result = json.loads(json_str)
                print(f"Parsed JSON for {step_name}: {result}")
                return result
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response for {step_name}: {e}")
                return {"is_match": False, "is_browser": False, "is_login_error": False}

        except Exception as e:
            print(f"Error in OpenRouter comparison for {step_name}: {e}")
            return {"is_match": False, "is_browser": False, "is_login_error": False}

    def detect_current_state(self):
        screenshot = self.capture_screenshot()
        
        logged_in_result = self.compare_with_openrouter(screenshot, self.reference_images["logged_in"], "logged_in")
        if logged_in_result.get("is_match", False):
            return "logged_in"
        
        if logged_in_result.get("is_login_error", False):
            return "login_error"
            
        password_result = self.compare_with_openrouter(screenshot, self.reference_images["password_screen"], "password_screen")
        if password_result.get("is_match", False):
            return "password"
            
        lms_result = self.compare_with_openrouter(screenshot, self.reference_images["lms_open"], "lms_open")
        if lms_result.get("is_match", False):
            return "lms"
            
        profile_result = self.compare_with_openrouter(screenshot, self.reference_images["profile_selected"], "profile_selected")
        if profile_result.get("is_match", False):
            return "profile"
            
        is_browser = any([
            result.get("is_browser", False) 
            for result in [logged_in_result, password_result, lms_result, profile_result]
            if result is not None and isinstance(result, dict)
        ])
        
        if is_browser:
            return "browser_other"
        else:
            return "not_browser"

    def smart_execute_flow(self):
        print("Analyzing current screen state...")
        current_state = self.detect_current_state()
        print(f"Detected state: {current_state}")
        
        if current_state == "logged_in":
            print("Already logged in! No further action needed.")
            return
            
        if current_state == "not_browser":
            print("Browser not detected. Starting complete flow...")
            self.openapp()
            time.sleep(3)
            self.attempt_login_flow()
            return
            
        if current_state == "profile":
            print("Profile screen detected. Continuing from profile selection...")
            self.openprofilecoord()
            time.sleep(2)
            self.openlms()
            time.sleep(2)
            self.attempt_login_with_retries()
            return
            
        if current_state == "browser_other":
            print("Browser detected but not on LMS. Opening LMS...")
            self.openlms()
            time.sleep(5)
            self.attempt_login_with_retries()
            return
            
        if current_state == "lms":
            print("LMS login screen detected. Continuing with password entry...")
            self.openlms()
            time.sleep(2)
            self.attempt_login_with_retries()
            return
            
        if current_state == "password":
            print("Password screen detected. Entering password...")
            self.attempt_login_with_retries()
            return
            
        if current_state == "login_error":
            print("Login error detected. Retrying login process...")
            self.attempt_login_with_retries()
            return
            
        print("Unknown state detected. Starting complete flow...")
        self.openapp()
        time.sleep(3)
        self.attempt_login_flow()

    def attempt_login_flow(self):
        self.openprofilecoord()
        time.sleep(5)
        self.openlms()
        time.sleep(5)
        self.attempt_login_with_retries()

    def attempt_login_with_retries(self):
        for attempt in range(1, self.max_login_attempts + 1):
            print(f"Login attempt {attempt} of {self.max_login_attempts}...")
            self.inputpassword(self.password)
            time.sleep(7)
            
            screenshot = self.capture_screenshot()
            result = self.compare_with_openrouter(screenshot, self.reference_images["logged_in"], "logged_in")
            
            if result.get("is_match", False):
                print("Successfully logged in!")
                return True
            
            if attempt < self.max_login_attempts:
                if result.get("is_login_error", False):
                    print(f"Login failed (attempt {attempt}). Retrying...")
                    time.sleep(3)
                    continue
                else:
                    current_state = self.detect_current_state()
                    if current_state == "logged_in":
                        print("Successfully logged in!")
                        return True
                    elif current_state == "password" or current_state == "lms":
                        print(f"Still at login screen (attempt {attempt}). Retrying...")
                    else:
                        print(f"Unknown state after login attempt {attempt}. Retrying...")
            else:
                print(f"Failed to log in after {self.max_login_attempts} attempts. Please check credentials or try manually.")
                return False

    def openapp(self):
        try:
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(chrome_path):
                subprocess.Popen([chrome_path], shell=True)
                print("Google Chrome opened successfully via subprocess")
            else:
                print(f"Chrome not found at {chrome_path}, please adjust the path")
        except Exception as e:
            print(f"Error opening Chrome: {e}")
        time.sleep(1)

    def openprofilecoord(self):
        try:
            po = pyautogui.locateCenterOnScreen(r"lmsopen\\buttons\\profilec.png", confidence=0.8)
            pyautogui.click(po, clicks=2, interval=1)
            print("Clicked on profile")
        except Exception as e:
            x, y = 717, 670
            pyautogui.moveTo(x, y, 1)
            pyautogui.doubleClick(x, y)
            print(f"Clicked on profile using coordinates due to: {e}")

    def openlms(self):
        try:
            x, y = 187, 30
            pyautogui.moveTo(x, y, 1)
            pyautogui.doubleClick(x, y)
            print("Opened LMS")
        except Exception as e:
            print(f"Error opening LMS: {e}")

    def inputpassword(self, password):
        """Enter both user ID and password on the same login screen"""
        try:
            # Try to find and click the user ID field first
            try:
                uid = pyautogui.locateCenterOnScreen(r"lmsopen\\buttons\\user.png", confidence=0.8)
                pyautogui.click(uid)
                print("Found user ID field using image recognition")
                time.sleep(1)
            except Exception as e:
                print(f"Could not find user ID field using image, using coordinates: {e}")
                x, y = 1352, 540  # Adjust these coordinates as needed
                pyautogui.click(x, y)
                time.sleep(1)
            
            # Clear any existing text and enter user ID
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            pyautogui.typewrite(self.user_id)
            print("Entered user ID")
            
            # Move to password field
            pyautogui.press('tab')
            time.sleep(1)
            
            # Try to find and click the password field
            try:
                pa = pyautogui.locateCenterOnScreen(r"lmsopen\\buttons\\pass.png", confidence=0.8)
                pyautogui.click(pa)
                print("Found password field using image recognition")
                time.sleep(1)
            except Exception as e:
                print(f"Could not find password field using image, using coordinates: {e}")
                x, y = 1355, 625  # Adjust these coordinates as needed
                pyautogui.click(x, y)
                time.sleep(1)
            
            # Clear any existing text and enter password
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('delete')
            pyautogui.typewrite(password)
            pyautogui.press('enter')
            print("Entered password and submitted")
            
        except Exception as e:
            print(f"Error during login input: {e}")

def main():
    try:
        LMSAutomator()
    except Exception as e:
        print(f"Fatal error in application: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()