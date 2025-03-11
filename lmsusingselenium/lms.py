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
from lmsusingselenium.driver import setup_driver
# def setup_driver():
#     options = webdriver.ChromeOptions()
#     options.add_argument("--start-maximized")
    
#     options.add_experimental_option("detach", True)  # Keeps browser open after script ends
    
#     # Block all permissions
#     options.add_argument("--disable-notifications")    
#     options.add_argument("--disable-features=ClipboardAPI")
#     options.add_argument("--disable-features=WebSensors")
#     options.add_argument("--use-fake-ui-for-media-stream")  # Denies camera/mic access
#     options.add_argument("--disable-features=GenericSensor")  # For motion sensors
#     options.add_argument("--disable-geolocation")  # Block location access
    
#     prefs = {
#         "profile.default_content_setting_values.clipboard": 2,  # 2 = block
#         "profile.default_content_setting_values.media_stream": 2,
#         "profile.default_content_setting_values.geolocation": 2,
#         "profile.default_content_setting_values.notifications": 2
        
#     }
#     options.add_experimental_option("prefs", prefs)
    
#     options.add_experimental_option("excludeSwitches", ["enable-automation"])
#     options.add_experimental_option("useAutomationExtension", False)
   
    
#     driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
#     driver.execute_cdp_cmd("Browser.grantPermissions", {
#         "permissions": [],
#         "origin": "https://iitjbsc.futurense.com"
#     })
    
#     # Get session ID
#     session_id = driver.session_id

#     # Save session ID to a file
#     with open("session.txt", "w") as file:
#         file.write(session_id)
    
#     # Save session ID and URL to a file
#     session_id = driver.session_id
#     executor_url = driver.command_executor._url  # Correct attribute

#     with open("session.txt", "w") as file:
#         file.write(f"{session_id}\n{executor_url}")
    
    # return driver

def login_to_lms():
    load_dotenv()
    USER_ID = os.getenv('USER_ID')
    PASSWORD = os.getenv('PASSWORD')
    
    if not USER_ID or not PASSWORD:
        raise ValueError("USER_ID or PASSWORD not found in .env file")

    driver = setup_driver()
    
    try:
        print("Navigating to login page...")
        driver.get('https://iitjbsc.futurense.com/login/index.php')
        
        wait = WebDriverWait(driver, 20)
        time.sleep(2)
        print("Filling username...")
        username_field = wait.until(EC.presence_of_element_located((By.ID, 'username')))
        username_field.clear()
        username_field.send_keys(USER_ID)
        
        time.sleep(2)
        print("Filling password...")
        password_field = driver.find_element(By.ID, 'password')
        password_field.clear()
        password_field.send_keys(PASSWORD)

        time.sleep(2)
        print("Clicking login button...")
        login_button = driver.find_element(By.ID, 'loginbtn')
        login_button.click()
        
        wait.until(EC.url_changes('https://iitjbsc.futurense.com/login/index.php'))
        
        current_url = driver.current_url
        print(f"Current URL after login: {current_url}")
        
        try:
            user_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.userbutton, #user-menu-toggle, .userpicture, .usertext'))
            )
            print("Login successful! Found user-related element.")
            return driver
        except:
            if 'login' not in current_url.lower():
                print("Login appears successful! No longer on login page.")
                return driver
            else:
                print("Login might have failed. Still on login page or unexpected URL.")
                print("Page source snapshot:", driver.page_source[:500])
                driver.quit()
                return None
                
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Page source snapshot:", driver.page_source[:500])
        driver.quit()
        return None

def select_and_navigate_to_subject(driver):
    subjects = {
        1: "Batch 01_B.Sc_Semester-1_Academic Information",
        2: "Batch-01_BSc_Semester-01_Algorithmic Thinking and its Applications",
        3: "Batch-01_BSc_Semester-01_Basics Of Data Analytics",
        4: "Batch-01_BSc_Semester-01_Foundations Of Statistics and Probability",
        5: "Batch-01_BSc_Semester-01_Linear Algebra and Numerical Analysis"
    }
    
    print("\nAvailable subjects:")
    for num, subject in subjects.items():
        print(f"{num}. {subject}")
    
    while True:
        try:
            time.sleep(5)
            selection = int(input("\nEnter the number of the subject you want to access (1-5): "))
            if 1 <= selection <= 5:
                selected_subject = subjects[selection]
                break
            else:
                print("Please enter a number between 1 and 5.")
        except ValueError:
            print("Please enter a valid number.")
    
    print(f"\nNavigating to: {selected_subject}")
    
    try:
        wait = WebDriverWait(driver, 50)  # Increased timeout
        current_url = driver.current_url
        print(f"Current URL before navigation: {current_url}")
        
        if "my" not in current_url.lower():
            print("Navigating to dashboard first...")
            dashboard_link = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[href*="my"], a[href*="dashboard"], a[aria-label*="dashboard"], .navbar-brand'))
            )
            dashboard_link.click()
            time.sleep(2)
        
        # Scroll to ensure all content is loaded
        print("Scrolling to load all course cards...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # Debug: Print all course names found on the page
        course_links = driver.find_elements(By.XPATH, "//a[contains(@class, 'card-img-link')]")
        print("Courses found on the page:")
        for link in course_links:
            try:
                course_name = link.find_element(By.CLASS_NAME, "sr-only").text.strip()
                print(f"- {course_name} (href: {link.get_attribute('href')})")
            except:
                print(f"- Unable to extract name for link: {link.get_attribute('href')}")
        
        print(f"Looking for subject link: {selected_subject}")
        subject_link = wait.until(
            EC.element_to_be_clickable((
                By.XPATH,
                f"//a[contains(@class, 'card-img-link') and .//span[@class='sr-only' and contains(text(), '{selected_subject}')]]"
            ))
        )
        print(f"Found subject link: {subject_link.get_attribute('href')}")
        
        # Scroll into view and click
        driver.execute_script("arguments[0].scrollIntoView();", subject_link)
        time.sleep(1)
        try:
            subject_link.click()
        except Exception as e:
            print(f"Standard click failed: {e}. Attempting JavaScript click...")
            driver.execute_script("arguments[0].click();", subject_link)
        
        print("Waiting for subject page to load...")
        wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//a[@role="menuitem" and contains(@class, "nav-link") and contains(@class, "active") and contains(@class, "active_tree_node") and contains(text(), "Course")]')
            )
        )
        
        course_link = driver.find_element(
            By.XPATH, 
            '//a[@role="menuitem" and contains(@class, "nav-link") and contains(@class, "active") and contains(@class, "active_tree_node") and contains(text(), "Course")]'
        )
        print(f"Found 'Course' navigation link: {course_link.get_attribute('outerHTML')}")
        print(f"Successfully navigated to {selected_subject}")
        return selected_subject
        
    except Exception as e:
        print(f"Error navigating to subject: {str(e)}")
        traceback.print_exc()
        print("Taking a screenshot for debugging...")
        driver.save_screenshot("navigation_error.png")
        with open("dashboard.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("Page source saved as 'dashboard.html'")
        return None

def navigate_to_self_paced_learning(driver):
    try:
        time.sleep(2)
        wait = WebDriverWait(driver, 10)
        print("Looking for 'Self Paced Learning' link...")
        
        driver.save_screenshot("before_self_paced.png")
        print("Screenshot saved as 'before_self_paced.png' for reference")
        
        try:
            self_paced_link = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Self Paced Learning')]"))
            )
        except:
            try:
                dropdown_items = driver.find_elements(By.CSS_SELECTOR, ".dropdown-item, .menu-item, .nav-item, li a")
                for item in dropdown_items:
                    if "self paced learning" in item.text.lower():
                        self_paced_link = item
                        break
                else:
                    raise Exception("Self Paced Learning link not found with alternative selectors")
            except:
                with open("course_page.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("Page source saved to 'course_page.html' for inspection")
                raise Exception("Self Paced Learning link not found")
        
        print("Found 'Self Paced Learning' link. Clicking...")
        driver.execute_script("arguments[0].scrollIntoView();", self_paced_link)
        driver.execute_script("arguments[0].click();", self_paced_link)
        
        time.sleep(2)
        print("Successfully navigated to Self Paced Learning section")
        return True
        
    except Exception as e:
        print(f"Error navigating to Self Paced Learning: {str(e)}")
        driver.save_screenshot("self_paced_error.png")
        return False

def select_and_open_module(driver):
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        print("Taking screenshot of self-paced learning page...")
        driver.save_screenshot("self_paced_learning.png")
        
        # Find all module sections using the specified class
        print("\nSearching for available modules...")
        section_headers = driver.find_elements(By.CSS_SELECTOR, "div.course-section-header.d-flex")
        
        if not section_headers:
            print("No section headers found. Saving page source for inspection...")
            with open("self_paced_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Page source saved to 'self_paced_page.html'")
            return None
        
        # Extract modules by looking for "Module-X" in the h3 elements
        modules = {}
        module_count = 0
        
        for i, header in enumerate(section_headers):
            try:
                # Try to find h3 inside the header
                h3_element = header.find_element(By.TAG_NAME, "h3")
                h3_text = h3_element.text.strip()
                
                # Use regex to extract module number
                module_match = re.search(r"Module-(\d+)", h3_text, re.IGNORECASE)
                
                if module_match:
                    module_count += 1
                    module_num = module_match.group(1)
                    module_name = f"Module-{module_num}"
                    
                    # Get the data-id attribute for identification
                    data_id = header.get_attribute("data-id")
                    data_number = header.get_attribute("data-number")
                    
                    modules[module_count] = {
                        "name": module_name,
                        "full_text": h3_text,
                        "element": header,
                        "data_id": data_id,
                        "data_number": data_number
                    }
                    
                    print(f"Found {module_name} (data-id: {data_id}, data-number: {data_number})")
            except Exception as e:
                print(f"Error processing header {i}: {str(e)}")
        
        if not modules:
            print("No modules found in the section headers. Trying alternative method...")
            # Try an alternative method to find modules
            module_elements = driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Module-') and (self::h3 or self::h4 or self::div or self::span or self::strong)]")
            
            for i, elem in enumerate(module_elements):
                module_text = elem.text.strip()
                module_match = re.search(r"Module-(\d+)", module_text, re.IGNORECASE)
                
                if module_match:
                    module_count += 1
                    module_num = module_match.group(1)
                    module_name = f"Module-{module_num}"
                    
                    # Find closest parent that might be clickable
                    parent = driver.execute_script(
                        "return arguments[0].closest('.course-section-header, a, button, .clickable, .toggler')", 
                        elem
                    )
                    
                    if not parent:
                        parent = elem
                    
                    modules[module_count] = {
                        "name": module_name,
                        "full_text": module_text,
                        "element": parent
                    }
        
        if not modules:
            print("No modules found with either method. Taking screenshot...")
            driver.save_screenshot("no_modules_found.png")
            return None
        
        print("\nAvailable modules:")
        for num, module_info in modules.items():
            print(f"{num}. {module_info['name']} - {module_info['full_text']}")
        
        # Get user module selection
        while True:
            try:
                module_selection = int(input(f"\nEnter the number of the module to access (1-{len(modules)}): "))
                if 1 <= module_selection <= len(modules):
                    selected_module = modules[module_selection]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(modules)}.")
            except ValueError:
                print("Please enter a valid number.")
        
        print(f"\nSelected: {selected_module['name']} - {selected_module['full_text']}")
        
        # Find the clickable element to open the module
        try:
            # Try to find a toggle button within the header
            toggle_button = selected_module['element'].find_element(By.CSS_SELECTOR, "a.btn, button.btn, .toggler, [data-toggle='collapse']")
            
            print(f"Found toggle button: {toggle_button.get_attribute('outerHTML')}")
            driver.execute_script("arguments[0].scrollIntoView();", toggle_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", toggle_button)
            print(f"Clicked on toggle button for {selected_module['name']}")
        except Exception as e:
            print(f"Toggle button not found or click failed: {e}. Trying direct click on section header...")
            try:
                driver.execute_script("arguments[0].scrollIntoView();", selected_module['element'])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", selected_module['element'])
                print(f"Clicked directly on section header for {selected_module['name']}")
            except Exception as e2:
                print(f"Direct click failed: {e2}. Trying to find any clickable element within the section...")
                try:
                    # Look for any potentially clickable element
                    clickable = selected_module['element'].find_element(By.CSS_SELECTOR, "a, button, [role='button'], .clickable")
                    driver.execute_script("arguments[0].scrollIntoView();", clickable)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", clickable)
                    print(f"Found and clicked on element within section for {selected_module['name']}")
                except Exception as e3:
                    print(f"All click attempts failed: {e3}")
                    print("Taking screenshot for debugging...")
                    driver.save_screenshot("click_failure.png")
        
        time.sleep(3)
        print(f"Module operation complete for: {selected_module['name']}")
        return selected_module['name']
        
    except Exception as e:
        print(f"Error selecting and opening module: {str(e)}")
        traceback.print_exc()
        driver.save_screenshot("module_open_error.png")
        return None

def select_and_open_week(driver):
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        print("\nSearching for available weeks...")
        section_headers = driver.find_elements(By.CSS_SELECTOR, "div.course-section-header.d-flex")
        
        if not section_headers:
            print("No section headers found for weeks. Saving page source for inspection...")
            with open("week_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Page source saved to 'week_page.html'")
            return None
        
        # Extract weeks by looking for "Week-X" in the h3 elements
        weeks = {}
        week_count = 0
        
        for i, header in enumerate(section_headers):
            try:
                # Try to find h3 inside the header
                h3_element = header.find_element(By.TAG_NAME, "h3")
                h3_text = h3_element.text.strip()
                
                # Use regex to extract week number
                week_match = re.search(r"Week-(\d+)", h3_text, re.IGNORECASE)
                
                if week_match:
                    week_count += 1
                    week_num = week_match.group(1)
                    week_name = f"Week-{week_num}"
                    
                    # Get the data-id attribute for identification
                    data_id = header.get_attribute("data-id")
                    data_number = header.get_attribute("data-number")
                    
                    weeks[week_count] = {
                        "name": week_name,
                        "full_text": h3_text,
                        "element": header,
                        "data_id": data_id,
                        "data_number": data_number
                    }
                    
                    print(f"Found {week_name} (data-id: {data_id}, data-number: {data_number})")
            except Exception as e:
                print(f"Error processing week header {i}: {str(e)}")
        
        if not weeks:
            print("No weeks found in the section headers. Trying alternative method...")
            # Try an alternative method to find weeks
            week_elements = driver.find_elements(By.XPATH, 
                "//*[contains(text(), 'Week-') and (self::h3 or self::h4 or self::div or self::span or self::strong)]")
            
            for i, elem in enumerate(week_elements):
                week_text = elem.text.strip()
                week_match = re.search(r"Week-(\d+)", week_text, re.IGNORECASE)
                
                if week_match:
                    week_count += 1
                    week_num = week_match.group(1)
                    week_name = f"Week-{week_num}"
                    
                    # Find closest parent that might be clickable
                    parent = driver.execute_script(
                        "return arguments[0].closest('.course-section-header, a, button, .clickable, .toggler')", 
                        elem
                    )
                    
                    if not parent:
                        parent = elem
                    
                    weeks[week_count] = {
                        "name": week_name,
                        "full_text": week_text,
                        "element": parent
                    }
        
        if not weeks:
            print("No weeks found with either method. Taking screenshot...")
            driver.save_screenshot("no_weeks_found.png")
            return None
        
        print("\nAvailable weeks:")
        for num, week_info in weeks.items():
            print(f"{num}. {week_info['name']} - {week_info['full_text']}")
        
        # Get user week selection
        while True:
            try:
                week_selection = int(input(f"\nEnter the number of the week to access (1-{len(weeks)}): "))
                if 1 <= week_selection <= len(weeks):
                    selected_week = weeks[week_selection]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(weeks)}.")
            except ValueError:
                print("Please enter a valid number.")
        
        print(f"\nSelected: {selected_week['name']} - {selected_week['full_text']}")
        
        # Find the clickable element to open the week
        try:
            # Try to find a toggle button within the header
            toggle_button = selected_week['element'].find_element(By.CSS_SELECTOR, "a.btn, button.btn, .toggler, [data-toggle='collapse']")
            
            print(f"Found toggle button: {toggle_button.get_attribute('outerHTML')}")
            driver.execute_script("arguments[0].scrollIntoView();", toggle_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", toggle_button)
            print(f"Clicked on toggle button for {selected_week['name']}")
        except Exception as e:
            print(f"Toggle button not found or click failed: {e}. Trying direct click on section header...")
            try:
                driver.execute_script("arguments[0].scrollIntoView();", selected_week['element'])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", selected_week['element'])
                print(f"Clicked directly on section header for {selected_week['name']}")
            except Exception as e2:
                print(f"Direct click failed: {e2}. Trying to find any clickable element within the section...")
                try:
                    # Look for any potentially clickable element
                    clickable = selected_week['element'].find_element(By.CSS_SELECTOR, "a, button, [role='button'], .clickable")
                    driver.execute_script("arguments[0].scrollIntoView();", clickable)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", clickable)
                    print(f"Found and clicked on element within section for {selected_week['name']}")
                except Exception as e3:
                    print(f"All click attempts failed: {e3}")
                    print("Taking screenshot for debugging...")
                    driver.save_screenshot("click_failure.png")
        
        time.sleep(3)
        print(f"Week operation complete for: {selected_week['name']}")
        return selected_week['name']
        
    except Exception as e:
        print(f"Error selecting and opening week: {str(e)}")
        traceback.print_exc()
        driver.save_screenshot("week_open_error.png")
        return None


def select_and_open_lecture(driver):
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        print("\nSearching for available lectures within the selected week containing Edpuzzle link...")
        driver.save_screenshot("lectures_page.png")
        
        # Find all activity items
        activity_blocks = driver.find_elements(By.CSS_SELECTOR, "div.activity-item")
        
        if not activity_blocks:
            print("No lectures found in activity items. Saving page source...")
            with open("week_content.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Page source saved to 'week_content.html'")
            return None
        
        # Extract lecture information, filtering only those containing the specific Edpuzzle icon
        lectures = {}
        lecture_count = 0
        
        for i, block in enumerate(activity_blocks):
            try:
                # Check if the block contains the Edpuzzle favicon image
                edpuzzle_icon = block.find_elements(By.CSS_SELECTOR, "img[src='https://edpuzzle.imgix.net/favicons/favicon-32.png']")
                if not edpuzzle_icon:
                    continue  # Skip this block if the icon is not found
                
                # Find the lecture link
                link_element = block.find_element(By.CSS_SELECTOR, "a.aalink.stretched-link")
                instance_element = link_element.find_element(By.CSS_SELECTOR, "span.instancename")
                lecture_title = instance_element.text.strip()
                
                # Remove the "External tool" text if present
                lecture_title = re.sub(r'\s*External tool\s*$', '', lecture_title)
                
                # Ensure the lecture has a valid name
                if not lecture_title:
                    continue  # Skip if no name is found
                
                # Ensure the link has an href attribute
                href_value = link_element.get_attribute("href")
                if href_value and href_value.strip():
                    lecture_count += 1
                    lecture_url = href_value
                    
                    lectures[lecture_count] = {
                        "title": lecture_title,
                        "element": link_element,
                        "url": lecture_url
                    }
                    
                    print(f"Found Edpuzzle lecture: {lecture_title} (URL: {lecture_url})")
                
            except Exception as e:
                print(f"Error processing activity block {i}: {str(e)}")
        
        if not lectures:
            print("No Edpuzzle lectures found. Taking screenshot...")
            driver.save_screenshot("no_edpuzzle_lectures.png")
            return None
        
        print("\nAvailable Edpuzzle lectures:")
        for num, lecture_info in lectures.items():
            print(f"{num}. {lecture_info['title']}")
        
        # Get user lecture selection
        while True:
            try:
                lecture_selection = int(input(f"\nEnter the number of the lecture to access (1-{len(lectures)}): "))
                if 1 <= lecture_selection <= len(lectures):
                    selected_lecture = lectures[lecture_selection]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(lectures)}.")
            except ValueError:
                print("Please enter a valid number.")
        
        print(f"\nSelected lecture: {selected_lecture['title']}")
        
        # Try to open the lecture
        try:
            print(f"Opening lecture: {selected_lecture['title']}")
            
            # Scroll into view and click
            driver.execute_script("arguments[0].scrollIntoView();", selected_lecture['element'])
            time.sleep(1)
            
            # Store the initial URL
            initial_url = driver.current_url
            
            # Try a direct click first
            try:
                selected_lecture['element'].click()
                print("Clicked on lecture link")
            except:
                # If direct click fails, try JavaScript click
                print("Direct click failed, trying JavaScript click...")
                driver.execute_script("arguments[0].click();", selected_lecture['element'])
                print("Used JavaScript to click on lecture link")
            
            time.sleep(3)  # Allow time for navigation
            
            # Verify if the lecture page has loaded by checking the header title
            try:
                lecture_header = driver.find_element(By.CSS_SELECTOR, "div.page-header-headings h1.h2").text.strip()
                if lecture_header == selected_lecture['title']:
                    print(f"Successfully opened lecture: {selected_lecture['title']}")
                    return selected_lecture['title']
                else:
                    print("Lecture title does not match. Trying direct URL navigation...")
            except:
                print("Could not verify lecture title. Trying direct URL navigation...")
            
        except Exception as e:
            print(f"Error opening lecture: {str(e)}")
            traceback.print_exc()
            driver.save_screenshot("lecture_open_error.png")
        
        # Try navigating directly to the URL as fallback
        try:
            print(f"Trying fallback: Navigating directly to lecture URL: {selected_lecture['url']}")
            driver.get(selected_lecture['url'])
            time.sleep(3)
            
            # Verify after direct navigation
            lecture_header = driver.find_element(By.CSS_SELECTOR, "div.page-header-headings h1.h2").text.strip()
            if lecture_header == selected_lecture['title']:
                print(f"Successfully navigated to {selected_lecture['title']}")
                return selected_lecture['title']
            else:
                print("Fallback navigation did not load the expected lecture.")
                return None
        except Exception as e2:
            print(f"Fallback navigation failed: {str(e2)}")
            return None
        
    except Exception as e:
        print(f"Error selecting and opening lecture: {str(e)}")
        traceback.print_exc()
        driver.save_screenshot("lecture_selection_error.png")
        return None


def play_video(driver):
    try:
        # Take a screenshot before switching to iframe for debugging
        driver.save_screenshot("before_iframe.png")
        
        # Switch to the iframe with improved error handling
        try:
            print("Attempting to switch to content iframe...")
            WebDriverWait(driver, 20).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "contentframe"))
            )
            print("Successfully switched to iframe")
        except Exception as iframe_error:
            print(f"Error switching to iframe by ID: {iframe_error}")
            print("Trying alternative iframe approach...")
            
            # Try to find iframe by tag name
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                print(f"Found {len(iframes)} iframes. Switching to first one...")
                driver.switch_to.frame(iframes[0])
                print("Successfully switched to first iframe")
            else:
                raise Exception("No iframes found on the page")
        
        # Take a screenshot inside iframe for debugging
        driver.save_screenshot("inside_iframe.png")
        
        # Wait for the play button to be clickable
        try:
            print("Looking for play button with original selector...")
            play_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".WG_g81ShVt"))
            )
            print("Found play button with original selector")
        except Exception as button_error:
            print(f"Original play button selector failed: {button_error}")
            print("Trying alternative play button selectors...")
            
            # Try alternative selectors for play button
            alternative_selectors = [
                "[aria-label='Play']",
                ".vjs-play-control",
                ".ytp-play-button",
                "button[title='Play']",
                ".play-button"
            ]
            
            play_button = None
            for selector in alternative_selectors:
                try:
                    print(f"Trying selector: {selector}")
                    play_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    print(f"Found play button with selector: {selector}")
                    break
                except:
                    continue
            
            if not play_button:
                # If all selectors fail, try direct JavaScript to play the video
                print("All play button selectors failed. Trying JavaScript play...")
                try:
                    driver.execute_script("document.querySelector('video').play();")
                    print("Started video playback via JavaScript")
                     # Allow video player controls to initialize
                    set_video_speed(driver)
                    
           
                    return  # Exit function early as we've handled everything via JavaScript
                except Exception as js_error:
                    print(f"JavaScript play failed: {js_error}")
                    raise Exception("Could not find or interact with play button")
        
        # Click the play button with JavaScript fallback
        try:
            play_button.click()
            print("Clicked play button directly")
        except Exception as click_error:
            print(f"Standard click failed: {click_error}. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", play_button)
            print("Clicked play button using JavaScript")
        
        print("Video started playing")
      
        set_video_speed(driver)    
       
    except Exception as e:
        print(f"An error occurred in play_video: {e}")
        traceback.print_exc()
        driver.save_screenshot("play_video_error.png")
        
        # Try to switch back to default content in case we're stuck in a frame
        try:
            driver.switch_to.default_content()
            print("Switched back to default content")
        except:
            pass

def set_video_speed(driver):
    try:
        print("Setting video speed to 2x...")
        # Wait for the speed control button to be available and click it
        speed_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".Y40-a18X9g, [aria-label='Playback Rate'], .playback-rate-button"))
        )
        
        # Try standard click with JavaScript fallback
        try:
            speed_button.click()
            print("Clicked speed button")
        except Exception as click_error:
            print(f"Standard click failed: {click_error}. Trying JavaScript click...")
            driver.execute_script("arguments[0].click();", speed_button)
            print("Clicked speed button using JavaScript")      
       
        # Look for the 2x option in the speed menu
        speed_options = driver.find_elements(By.CSS_SELECTOR, ".playback-rate-menu button, .speed-option, [role='menuitemradio']")
        
        for option in speed_options:
            if "2" in option.text or "2.0" in option.text or "2x" in option.text.lower():
                print(f"Clicking on speed option: {option.text}")
                
                # Try standard click with JavaScript fallback
                try:
                    option.click()
                    print("Clicked 2x option")
                except Exception as option_click_error:
                    print(f"Standard click on option failed: {option_click_error}. Trying JavaScript click...")
                    driver.execute_script("arguments[0].click();", option)
                    print("Clicked 2x option using JavaScript")
                    
                print("Video speed set to 2x")
                return True
        
        # If UI interaction fails, try direct JavaScript approach
        print("2x speed option not found or couldn't be clicked. Trying JavaScript approach...")
        try:
            driver.execute_script("document.querySelector('video').playbackRate = 2.0;")
            print("Set playback speed to 2x via JavaScript")
            return True
        except Exception as js_error:
            print(f"JavaScript speed setting failed: {js_error}")
            driver.save_screenshot("speed_options.png")
            return False
        
    except Exception as e:
        print(f"Error setting video speed: {str(e)}")
        traceback.print_exc()
        driver.save_screenshot("speed_error.png")
        
        # Try direct JavaScript approach as last resort
        try:
            driver.execute_script("document.querySelector('video').playbackRate = 2.0;")
            print("Set playback speed to 2x via JavaScript fallback")
            return True
        except:
            return False
