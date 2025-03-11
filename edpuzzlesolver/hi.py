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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Read session ID from file
with open("session.txt", "r") as file:
    session_id = file.read().strip()

# Try to attach to existing browser session
try:
    driver = webdriver.Remote(command_executor="http://localhost:9515", options=webdriver.ChromeOptions())
    driver.session_id = session_id
    print(f"Successfully attached to existing browser session: {session_id}")
except Exception as e:
    print(f"Failed to attach to existing session: {e}")
    # Fallback to creating a new session if needed
    driver = webdriver.Chrome()
    # Save the new session ID
    with open("session.txt", "w") as file:
        file.write(driver.session_id)
    print(f"Created new browser session: {driver.session_id}")

# Set pyautogui pause to ensure actions are not too fast
pyautogui.PAUSE = 0.5

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
    def __init__(self, config, driver):
        self.config = config
        self.driver = driver
        self.groq_processor = GroqProcessor(config)
        self.ollama_processor = OllamaProcessor(config)
        self.history = []
        self.run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.screenshot_folder = os.path.join("screenshots", self.run_timestamp)
        os.makedirs(self.screenshot_folder, exist_ok=True)
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
    def __init__(self, config, driver):
        self.root = tk.Tk()
        self.root.title("Assistant")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        self.driver = driver
        self.image_processor = ImageProcessor(config, driver)
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
        try:
            # Assume options are in a list or radio buttons with text content
            option_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//*[contains(@class, 'option') or @type='radio' or @type='checkbox']"))
            )
            
            for element in option_elements:
                option_text = element.text.strip().lower().rstrip('.')
                if answer in option_text:
                    element.click()
                    print(f"Clicked option: {option_text}")
                    
                    # Try to find and click the submit button
                    try:
                        submit_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit') or contains(@class, 'submit')]"))
                        )
                        submit_button.click()
                        print("Clicked Submit button")
                    except Exception as e:
                        print(f"Could not find or click Submit button: {e}")
                    return
            
            print(f"No matching option found for answer '{answer}'")
        except Exception as e:
            print(f"Error selecting option: {e}")

    def process_detection(self):
        try:
            self.speech_manager.announce("Processing image")
            screenshot_path = self.image_processor.take_screenshot()
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
    
    def run(self):
        self.root.mainloop()

def main():
    print("Starting Assistant...")
    print("Features:")
    print("- Click 'Detect' or say 'wake up' to process screen and auto-select answer")
    print("- Click 'Silence' or say 'silence' to stop speaking")
    print("- Click 'Close' or say 'close' to exit")
    
    config = Config()
    app = FloatingUI(config, driver)
    app.run()

if __name__ == "__main__":
    main()