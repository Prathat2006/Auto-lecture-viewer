import base64
import pyautogui
import speech_recognition as sr
import pyttsx3
import ollama
from groq import Groq
import configparser
import os
from dotenv import load_dotenv
import threading
import tkinter as tk
from abc import ABC, abstractmethod
import json
from datetime import datetime
import time
import cv2
import numpy as np
import pytesseract
import mss
from PIL import Image

# Set pyautogui pause to ensure actions are not too fast
pyautogui.PAUSE = 0.5

# Path to Tesseract executable (update this based on your installation)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows example

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        load_dotenv()
        
        self.GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        self.preferred_source = self.config.get('llms', 'preferred_source', fallback='groq').lower()
        self.temperature = float(self.config.get('llms', 'temperature', fallback='0.0'))
        
        self.GROQ_VISION_MODEL = self.config.get('groq', 'VISION_MODEL', fallback='llama-3.2-90b-vision-preview')
        self.GROQ_ANSWER_MODEL = self.config.get('groq', 'ANSWER_MODEL', fallback='llama-3.3-70b-versatile')
        self.OLLAMA_VISION_MODEL = self.config.get('ollama', 'VISION_MODEL', fallback='llama3.2-vision:latest')
        self.OLLAMA_ANSWER_MODEL = self.config.get('ollama', 'ANSWER_MODEL', fallback='mistral:latest')

class LLMProcessor(ABC):
    @abstractmethod
    def process_image(self, image_path):
        pass
    
    @abstractmethod
    def get_answer(self, question_and_options):
        pass

class GroqProcessor(LLMProcessor):
    def __init__(self, config):
        self.config = config
        if not config.GROQ_API_KEY:
            raise ValueError("Groq API key not found")
        self.client = Groq(api_key=config.GROQ_API_KEY)
    
    def process_image(self, image_path):
        base64_image = self._encode_image(image_path)
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract the question and options from this image. List each option exactly as it appears, including any leading symbols like '*', one per line."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                },
                            },
                        ],
                    }
                ],
                model=self.config.GROQ_VISION_MODEL,
                temperature=self.config.temperature
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            print(f"Error with Groq API: {e}")
            raise
    
    def get_answer(self, question_and_options):
        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Provide only the final answer (the exact text of the chosen option, excluding any leading symbols like '*') without any explanation."},
                    {"role": "user", "content": question_and_options}
                ],
                model=self.config.GROQ_ANSWER_MODEL,
                temperature=self.config.temperature
            )
            return chat_completion.choices[0].message.content.strip().lower()
        except Exception as e:
            print(f"Error with Groq API: {e}")
            raise
    
    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

class OllamaProcessor(LLMProcessor):
    def __init__(self, config):
        self.config = config
    
    def process_image(self, image_path):
        base64_image = self._encode_image(image_path)
        try:
            response = ollama.chat(
                model=self.config.OLLAMA_VISION_MODEL,
                messages=[
                    {"role": "system", "content": "Extract questions and options from images. List each option exactly as it appears, including any leading symbols like '*', one per line."},
                    {"role": "user", "content": f"data:image/jpeg;base64,{base64_image}"}
                ]
            )
            return response['message']['content']
        except Exception as e:
            print(f"Error with Ollama: {e}")
            raise
    
    def get_answer(self, question_and_options):
        try:
            response = ollama.chat(
                model=self.config.OLLAMA_ANSWER_MODEL,
                messages=[
                    {"role": "system", "content": "Provide only the final answer (the exact text of the chosen option, excluding any leading symbols like '*') without any explanation."},
                    {"role": "user", "content": question_and_options}
                ]
            )
            return response['message']['content'].strip().lower()
        except Exception as e:
            print(f"Error with Ollama: {e}")
            raise
    
    def _encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

class ImageProcessor:
    def __init__(self, config):
        self.config = config
        self.groq_processor = GroqProcessor(config)
        self.ollama_processor = OllamaProcessor(config)
        self.history = []
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_folder = os.path.join("screenshots", self.run_timestamp)
        self.option_screenshot_folder = os.path.join("option_screenshots", self.run_timestamp)
        os.makedirs(self.screenshot_folder, exist_ok=True)
        os.makedirs(self.option_screenshot_folder, exist_ok=True)
        self.history_file = os.path.join("history", f"conversation_history_{self.run_timestamp}.json")
        os.makedirs("history", exist_ok=True)

    def save_history(self):
        with open(self.history_file, "w") as history_file:
            json.dump(self.history, history_file, indent=4)
    
    def take_screenshot(self):
        """Take full screen screenshot for LLM processing"""
        screenshot_path = os.path.join(self.screenshot_folder, f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(screenshot_path)
        print(f"Full screenshot saved as {screenshot_path}")
        return screenshot_path
    
    def take_right_side_screenshot(self):
        """Take screenshot of just the right side for OCR processing"""
        full_screenshot_path = self.take_screenshot()  # We still need the full screenshot for LLM
        
        # Read the full screenshot
        full_img = cv2.imread(full_screenshot_path)
        height, width = full_img.shape[:2]
        
        # Calculate right side dimensions (approximately 30% of screen width)
        right_side_width = int(width * 0.3)
        right_side_x = width - right_side_width
        
        # Crop to just the right side where questions appear
        right_side_img = full_img[:, right_side_x:width]
        
        # Save the cropped version for OCR
        right_side_path = os.path.join(self.screenshot_folder, f"right_side_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        cv2.imwrite(right_side_path, right_side_img)
        
        print(f"Right side screenshot saved as {right_side_path}")
        return full_screenshot_path  # Return the full screenshot path for LLM processing
    
    def process_image(self, image_path):
        errors = []
        if self.config.preferred_source == 'groq':
            try:
                result = self.groq_processor.process_image(image_path)
                self.history.append({"screenshot": image_path, "question_and_options": result})
                self.save_history()
                return result
            except Exception as e:
                errors.append(f"Groq: {str(e)}")
                try:
                    result = self.ollama_processor.process_image(image_path)
                    self.history.append({"screenshot": image_path, "question_and_options": result})
                    self.save_history()
                    return result
                except Exception as e:
                    errors.append(f"Ollama: {str(e)}")
                    return f"Unable to process image. Errors: {'; '.join(errors)}"
        else:
            try:
                result = self.ollama_processor.process_image(image_path)
                self.history.append({"screenshot": image_path, "question_and_options": result})
                self.save_history()
                return result
            except Exception as e:
                errors.append(f"Ollama: {str(e)}")
                try:
                    result = self.groq_processor.process_image(image_path)
                    self.history.append({"screenshot": image_path, "question_and_options": result})
                    self.save_history()
                    return result
                except Exception as e:
                    errors.append(f"Groq: {str(e)}")
                    return f"Unable to process image. Errors: {'; '.join(errors)}"
    
    def get_answer(self, question_and_options):
        errors = []
        if self.config.preferred_source == 'groq':
            try:
                answer = self.groq_processor.get_answer(question_and_options)
                self.history[-1]["answer"] = answer
                self.save_history()
                return answer
            except Exception as e:
                errors.append(f"Groq: {str(e)}")
                try:
                    answer = self.ollama_processor.get_answer(question_and_options)
                    self.history[-1]["answer"] = answer
                    self.save_history()
                    return answer
                except Exception as e:
                    errors.append(f"Ollama: {str(e)}")
                    return f"Unable to get answer. Errors: {'; '.join(errors)}"
        else:
            try:
                answer = self.ollama_processor.get_answer(question_and_options)
                self.history[-1]["answer"] = answer
                self.save_history()
                return answer
            except Exception as e:
                errors.append(f"Ollama: {str(e)}")
                try:
                    answer = self.groq_processor.get_answer(question_and_options)
                    self.history[-1]["answer"] = answer
                    self.save_history()
                    return answer
                except Exception as e:
                    errors.append(f"Groq: {str(e)}")
                    return f"Unable to get answer. Errors: {'; '.join(errors)}"

    def capture_screen(self, monitor_index=1):
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            return img

    def preprocess_image(self, img_cv):
        gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return thresh

def find_and_crop_option(self, target_text, option_index=None, padding=10):
        print(f"Capturing screen to find option: {target_text}")
        try:
            # Capture full screen
            img_pil = self.capture_screen()
            img_cv = np.array(img_pil)
            
            # Get screen dimensions
            screen_height, screen_width = img_cv.shape[:2]
            
            # Define the right side area (approximately 30% of the screen width)
            right_side_width = int(screen_width * 0.3)
            right_side_x = screen_width - right_side_width
            
            # Crop to just the right side where questions and options appear
            right_side_img = img_cv[:, right_side_x:screen_width]
            
            print("Preprocessing image for OCR...")
            processed_img = self.preprocess_image(right_side_img)
            
            print("Running OCR...")
            custom_config = r'--oem 3 --psm 6'
            data = pytesseract.image_to_data(processed_img, config=custom_config, output_type=pytesseract.Output.DICT)
            extracted_text = pytesseract.image_to_string(processed_img, config=custom_config)
            print("Extracted Text from Screen:\n", extracted_text)
            
            # Normalize target text (remove trailing period and extra whitespace)
            target_text_normalized = target_text.strip().rstrip('.').lower()
            
            for i in range(len(data['text'])):
                ocr_text = data['text'][i].strip().rstrip('.').lower()
                if ocr_text and (target_text_normalized in ocr_text or ocr_text in target_text_normalized):
                    # These coordinates are relative to the cropped image
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    x_start, y_start = max(x - padding, 0), max(y - padding, 0)
                    x_end, y_end = min(x + w + padding, right_side_img.shape[1]), min(y + h + padding, right_side_img.shape[0])
                    
                    # Create cropped image of just the option
                    cropped_img = right_side_img[y_start:y_end, x_start:x_end]
                    if option_index is not None:
                        # Use option_index to name the file
                        option_name = f"option_{option_index}"
                    else:
                        option_name = f"option_{target_text.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    option_path = os.path.join(self.option_screenshot_folder, f"{option_name}.png")
                    cv2.imwrite(option_path, cv2.cvtColor(cropped_img, cv2.COLOR_RGB2BGR))
                    print(f"Screenshot saved as {option_path}")
                    
                    # Convert back to global screen coordinates for clicking
                    global_center_x = right_side_x + x_start + (x_end - x_start) // 2
                    global_center_y = y_start + (y_end - y_start) // 2
                    return option_path, (global_center_x, global_center_y)
            
            print(f"Option '{target_text}' not found on the screen.")
            return None, None
        except Exception as e:
            print(f"Error in find_and_crop_option: {e}")
            return None, None
class SpeechManager:
    def __init__(self):
        self.speaking = False
        self.running = True
        self.recognizer = sr.Recognizer()
        self.mic = sr.Microphone()
    
    def announce(self, text):
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            engine.setProperty('voice', voices[1].id)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"Error in announcement: {e}")
    
    def speak_answer(self, answer):
        self.speaking = True
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        engine.setProperty('voice', voices[1].id)
        try:
            engine.say(answer)
            engine.runAndWait()
        except:
            pass
        finally:
            self.speaking = False
            self.announce("Listening for wake up.")
    
    def stop_speaking(self):
        if self.speaking:
            engine = pyttsx3.init()
            engine.stop()
            self.speaking = False
            self.announce("Silenced. Listening for wake up.")
    
    def listen_for_commands(self, callback_detect, callback_silence, callback_close):
        while self.running:
            with self.mic as source:
                print("Listening for voice commands...")
                try:
                    audio = self.recognizer.listen(source)
                    command = self.recognizer.recognize_google(audio).lower()
                    if "wake up" in command:
                        callback_detect()
                    elif "silence" in command and self.speaking:
                        callback_silence()
                    elif "close" in command:
                        callback_close()
                except sr.UnknownValueError:
                    pass
                except Exception as e:
                    print(f"Error in speech recognition: {e}")

class FloatingUI:
    def __init__(self, config):
        self.root = tk.Tk()
        self.root.title("Assistant")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        self.image_processor = ImageProcessor(config)
        self.speech_manager = SpeechManager()
        
        self.setup_ui()
        
        self.speech_thread = threading.Thread(
            target=self.speech_manager.listen_for_commands,
            args=(self.handle_detect, self.handle_silence, self.handle_close),
            daemon=True
        )
        self.speech_thread.start()
    
    def setup_ui(self):
        self.frame = tk.Frame(self.root, bg='#2c3e50')
        self.frame.pack(padx=5, pady=5)
        
        self.detect_btn = tk.Button(self.frame, text="Detect", command=self.handle_detect,
                                  bg='#3498db', fg='white', width=10)
        self.detect_btn.pack(side=tk.LEFT, padx=2)
        
        self.silence_btn = tk.Button(self.frame, text="Silence", command=self.handle_silence,
                                   bg='#e74c3c', fg='white', width=10)
        self.silence_btn.pack(side=tk.LEFT, padx=2)
        
        self.close_btn = tk.Button(self.frame, text="Close", command=self.handle_close,
                                 bg='#95a5a6', fg='white', width=10)
        self.close_btn.pack(side=tk.LEFT, padx=2)
        
        self.frame.bind('<Button-1>', self.start_drag)
        self.frame.bind('<B1-Motion>', self.drag)
    
    def start_drag(self, event):
        self.x = event.x
        self.y = event.y
    
    def drag(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
    
    def handle_detect(self):
        threading.Thread(target=self.process_detection, daemon=True).start()
    
    def handle_silence(self):
        self.speech_manager.stop_speaking()
    
    def handle_close(self):
        self.speech_manager.running = False
        self.speech_manager.announce("Closing now..")
        self.root.after(1000, self.root.quit)
    
    def get_options_from_extracted_text(self, question_and_options):
        options = []
        for line in question_and_options.split('\n'):
            line = line.strip()
            if line.startswith('*'):
                option = line.lstrip('*').strip()
                if option and not option.startswith('MULTIPLE-CHOICE QUESTION') and not any(q in option.lower() for q in ['question', 'represents']):
                    options.append(option)
        return options
    def select_option(self, answer, options):
        option_mapping = {}
        
        # Save the first item as the question (option_0)
        question_text = question_and_options.split('\n')[0].strip()  # Assuming first line is the question
        question_path, _ = self.image_processor.find_and_crop_option(question_text, option_index=0)
        if question_path:
            option_mapping["option_0"] = question_text
            print(f"Question saved as {question_path}")
        
        # Save each option as option_1, option_2, etc.
        for idx, option in enumerate(options, start=1):
            option_path, _ = self.image_processor.find_and_crop_option(option, option_index=idx)
            if option_path:
                option_mapping[f"option_{idx}"] = option
                print(f"Option {idx} saved as {option_path}")
        
        # Map the answer to the correct option and click it
        for option_key, option_text in option_mapping.items():
            if option_key == "option_0":  # Skip the question
                continue
            if answer.lower().rstrip('.') in option_text.lower().rstrip('.'):
                option_path = os.path.join(self.image_processor.option_screenshot_folder, f"{option_key}.png")
                print(f"Matched answer '{answer}' with {option_key}: '{option_text}'")
                
                try:
                    # Use pyautogui.locateOnScreen to find the option on the screen
                    location = pyautogui.locateCenterOnScreen(option_path, confidence=0.7)
                    if location:
                        pyautogui.moveTo(location)
                        pyautogui.click()
                        print(f"Clicked {option_key} at {location}")
                        
                        # Attempt to click the submit button
                        time.sleep(1)
                        try:
                            submit_location = pyautogui.locateCenterOnScreen('templates/submit.png', confidence=0.7)
                            if submit_location:
                                pyautogui.moveTo(submit_location)
                                pyautogui.click()
                                print("Clicked on Submit button")
                            else:
                                print("Could not locate Submit button")
                        except Exception as e:
                            print(f"Error locating Submit button: {e}")
                        return
                    else:
                        print(f"Could not locate {option_key} on screen")
                except Exception as e:
                    print(f"Error locating {option_key}: {e}")
        
        print(f"No matching option found for answer '{answer}'")

    def process_detection(self):
        try:
            self.speech_manager.announce("Processing image")
            # Take full screenshot for LLM processing
            screenshot_path = self.image_processor.take_screenshot()
            global question_and_options  # Make it global so select_option can access it
            question_and_options = self.image_processor.process_image(screenshot_path)
            print("\nExtracted Text:\n", question_and_options)
            
            options = self.get_options_from_extracted_text(question_and_options)
            if not options:
                print("No valid options extracted from the image.")
                return
            answer = self.image_processor.get_answer(question_and_options)
            print("\nFinal Answer:\n", answer)
            
            time.sleep(1)
            self.select_option(answer, options)
            
            self.speech_manager.speak_answer(answer)
        except Exception as e:
            print(f"Error in detection: {e}")

def main():
    print("Starting Assistant...")
    print("Features:")
    print("- Click 'Detect' or say 'wake up' to process screen and auto-select answer")
    print("- Click 'Silence' or say 'silence' to stop speaking")
    print("- Click 'Close' or say 'close' to exit")
    
    config = Config()
    app = FloatingUI(config)
    app.run()

if __name__ == "__main__":
    main()