from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
from dotenv import load_dotenv
import os
import traceback
import re
from selenium.webdriver import ActionChains

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    
    options.add_experimental_option("detach", True)  # Keeps browser open after script ends
    
    # Block all permissions
    options.add_argument("--disable-notifications")    
    options.add_argument("--disable-features=ClipboardAPI")
    options.add_argument("--disable-features=WebSensors")
    options.add_argument("--use-fake-ui-for-media-stream")  # Denies camera/mic access
    options.add_argument("--disable-features=GenericSensor")  # For motion sensors
    options.add_argument("--disable-geolocation")  # Block location access
    
    prefs = {
        "profile.default_content_setting_values.clipboard": 2,  # 2 = block
        "profile.default_content_setting_values.media_stream": 2,
        "profile.default_content_setting_values.geolocation": 2,
        "profile.default_content_setting_values.notifications": 2
        
    }
    options.add_experimental_option("prefs", prefs)
    
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
   
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    driver.execute_cdp_cmd("Browser.grantPermissions", {
        "permissions": [],
        "origin": "https://iitjbsc.futurense.com"
    })
    
    # Get session ID
    session_id = driver.session_id

    # Save session ID to a file
    with open("session.txt", "w") as file:
        file.write(session_id)
    
    # Save session ID and URL to a file
    session_id = driver.session_id
  

    with open("session.txt", "w") as file:
        file.write(f"{session_id}")
    
    return driver