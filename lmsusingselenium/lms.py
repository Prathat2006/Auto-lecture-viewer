from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from dotenv import load_dotenv
import os
import traceback

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
    
    return driver

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
            time.sleep(2)
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
        wait = WebDriverWait(driver, 30)  # Increased timeout
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

def get_and_select_week(driver):
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(2)
        
        # Print html source of a small section for debugging
        print("Taking screenshot of current page for reference...")
        driver.save_screenshot("before_weeks.png")
        
        # More specific XPATH that targets the course section headers and extracts their data
        print("\nSearching for available weeks...")
        week_elements = driver.find_elements(By.CSS_SELECTOR, ".course-section-header[data-for='section_title']")
        
        if not week_elements:
            print("No week elements found. Trying alternative selector...")
            week_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Week-')]")
        
        # Extract week names and organize them
        weeks = {}
        for i, elem in enumerate(week_elements):
            try:
                # Try to find the h3 within the section header
                h3_elem = elem.find_element(By.CSS_SELECTOR, "h3.sectionname")
                week_name = h3_elem.text.strip()
                # If week_name is empty, try getting the aria-label from the button
                if not week_name:
                    try:
                        button = elem.find_element(By.CSS_SELECTOR, "a[aria-label]")
                        week_name = button.get_attribute("aria-label")
                    except:
                        week_name = f"Week {i+1}"
            except:
                # If h3 not found, try getting text directly or use default
                week_name = elem.text.strip() or f"Week {i+1}"
                
            # Try to extract week number if possible
            if "Week-" not in week_name and elem.get_attribute("data-number"):
                data_number = elem.get_attribute("data-number")
                week_name = f"Week-{data_number}"
                
            weeks[i+1] = {"name": week_name, "element": elem}
        
        if not weeks:
            print("No week elements found. Taking screenshot and saving page source...")
            driver.save_screenshot("no_weeks_found.png")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("Saved page source to 'page_source.html'")
            return None
            
        # Display available weeks to user
        print("\nAvailable weeks:")
        for num, week_info in weeks.items():
            print(f"{num}. {week_info['name']}")
        
        # Get user selection
        while True:
            try:
                selection = int(input(f"\nEnter the number of the week to access (1-{len(weeks)}): "))
                if 1 <= selection <= len(weeks):
                    selected_week = weeks[selection]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(weeks)}.")
            except ValueError:
                print("Please enter a valid number.")
        
        print(f"\nSelected: {selected_week['name']}")
        
        # First try to find and click the collapse/expand button
        try:
            # Look for the collapse/expand button within the week element
            expand_button = selected_week['element'].find_element(By.CSS_SELECTOR, "a[data-toggle='collapse']")
            driver.execute_script("arguments[0].scrollIntoView();", expand_button)
            time.sleep(1)
            print(f"Clicking expand button for {selected_week['name']}...")
            expand_button.click()
        except Exception as e:
            print(f"Couldn't find expand button: {e}. Trying alternative method...")
            try:
                # If button not found, try clicking the week element directly
                driver.execute_script("arguments[0].scrollIntoView();", selected_week['element'])
                time.sleep(1)
                driver.execute_script("arguments[0].click();", selected_week['element'])
                print("Clicked week element directly")
            except Exception as e2:
                print(f"Direct click failed: {e2}. Trying to find clickable element within...")
                try:
                    # Try finding any clickable element inside
                    clickable = selected_week['element'].find_element(By.CSS_SELECTOR, "a, button, h3")
                    driver.execute_script("arguments[0].scrollIntoView();", clickable)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", clickable)
                    print("Found and clicked element inside week container")
                except Exception as e3:
                    print(f"All click attempts failed: {e3}")
                    print("Taking screenshot of failure point...")
                    driver.save_screenshot("week_click_failure.png")
        
        time.sleep(3)
        print(f"Navigation to {selected_week['name']} attempted")
        return selected_week['name']
        
    except Exception as e:
        print(f"Error finding or selecting week: {str(e)}")
        traceback.print_exc()
        driver.save_screenshot("week_error.png")
        return None
def expand_section_if_collapsed(driver, section_element):
    """Helper function to expand a collapsed section"""
    try:
        # Check if section is collapsed
        parent_div = driver.execute_script("return arguments[0].closest('.course-section-header')", section_element)
        collapsed_btn = parent_div.find_element(By.CSS_SELECTOR, "a.collapsed")
        
        if collapsed_btn:
            print("Section is collapsed. Expanding...")
            driver.execute_script("arguments[0].click();", collapsed_btn)
            time.sleep(1)
            return True
    except:
        # Section might already be expanded or structure is different
        pass
    
    return False
def find_and_play_lectures(driver):
    try:
        wait = WebDriverWait(driver, 10)
        time.sleep(3)
        
        print("Looking for lecture videos...")
        video_elements = driver.find_elements(By.CSS_SELECTOR, "video, .video-js, iframe[src*='video'], a[href*='.mp4']")
        
        if not video_elements:
            print("No direct video elements found. Looking for links...")
            video_elements = driver.find_elements(By.XPATH, "//a[contains(text(), 'Lecture') or contains(text(), 'Video')]")
        
        lectures = {i + 1: {"element": elem, "name": elem.text.strip() or f"Video Element {i + 1}"} for i, elem in enumerate(video_elements)}
        
        if lectures:
            print("\nPotential lecture videos found:")
            for num, lecture_info in lectures.items():
                print(f"{num}. {lecture_info['name']}")
            
            selection = int(input(f"\nEnter the number of the lecture to play (1-{len(lectures)}) or 0 to exit: "))
            if selection == 0:
                return None
            selected_lecture = lectures[selection]
            
            print(f"\nSelected lecture: {selected_lecture['name']}")
            lecture_element = selected_lecture['element']
            driver.execute_script("arguments[0].scrollIntoView();", lecture_element)
            
            if lecture_element.tag_name.lower() == 'video':
                driver.execute_script("arguments[0].play();", lecture_element)
            else:
                lecture_element.click()
            
            time.sleep(3)
            print("Lecture navigation complete.")
            return True
        else:
            print("No lecture videos found.")
            return None
            
    except Exception as e:
        print(f"Error finding or playing lectures: {str(e)}")
        driver.save_screenshot("lecture_play_error.png")
        return None

def main():
    print("Starting LMS automation...")
    driver = login_to_lms()
    
    if driver:
        try:
            selected_subject = select_and_navigate_to_subject(driver)
            if not selected_subject:
                print("Failed to navigate to subject. Exiting.")
                return
                
            if not navigate_to_self_paced_learning(driver):
                print("Failed to navigate to Self Paced Learning. Exiting.")
                return
                
            selected_week = get_and_select_week(driver)
            if not selected_week:
                print("Failed to select a week. Exiting.")
                return
                
            find_and_play_lectures(driver)
            
            print("\nAutomation sequence complete. Browser will remain open.")
            
        except Exception as e:
            print(f"An error occurred during automation: {str(e)}")
            driver.save_screenshot("automation_error.png")
    else:
        print("Login failed. Cannot proceed with navigation.")

if __name__ == "__main__":
    main()