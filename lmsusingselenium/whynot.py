import os
import json
import time
import re
from threading import Timer, Lock
from lmsusingselenium.driver import setup_driver
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from edpuzzlesolver.llminit import LLMManager

interaction_timing = {
    "scheduled_timers": [],
    "timing_lock": Lock()
}

a = 15

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_-]', '', name[:50])

def extract_interaction_times(driver):
    try:
        time.sleep(3)
        interaction_container = driver.find_element(By.CSS_SELECTOR, "div.OLRXd3vFHv")
        interaction_markers = interaction_container.find_elements(
            By.CSS_SELECTOR, 
            "div[role='button'][aria-label^='Interaction at'], div[role='button'][aria-label^='Multiple interactions at']"
        )
        
        if not interaction_markers:
            print("No interaction markers found.")
            return []
            
        interaction_times = []
        for marker in interaction_markers:
            aria_label = marker.get_attribute('aria-label')
            single_match = re.search(r'Interaction at (\d+) seconds', aria_label)
            multiple_match = re.search(r'Multiple interactions at (\d+) seconds', aria_label)
            
            if single_match:
                seconds = int(single_match.group(1))
                interaction_times.append(seconds)
                print(f"Found single interaction at {seconds}s")
            elif multiple_match:
                seconds = int(multiple_match.group(1))
                interaction_times.append(seconds)
                print(f"Found multiple interactions at {seconds}s")
        
        if not interaction_times:
            print("Failed to extract interaction times.")
            return []
            
        interaction_times.sort()
        print(f"Extracted interaction times: {interaction_times}")
        
        schedule_interactions(driver, interaction_times)
        return interaction_times
        
    except Exception as e:
        print(f"Error extracting interaction times: {str(e)}")
        driver.save_screenshot("interaction_extraction_error.png")
        return []

def schedule_interactions(driver, interaction_times):
    with interaction_timing["timing_lock"]:
        for timer in interaction_timing["scheduled_timers"]:
            timer.cancel()
        interaction_timing["scheduled_timers"].clear()
        
        current_time = driver.execute_script("return document.querySelector('video').currentTime;")
        playback_rate = driver.execute_script("return document.querySelector('video').playbackRate;")
        print(f"Current video time: {current_time:.2f}s, Playback rate: {playback_rate}x")
        
        for interaction_time in interaction_times:
            if interaction_time > current_time:
                wait_seconds = (interaction_time - current_time) / playback_rate
                print(f"Scheduling interaction at {interaction_time}s (wait: {wait_seconds:.2f}s)")
                
                timer = Timer(wait_seconds, process_interaction, args=[driver, interaction_time])
                timer.daemon = True
                timer.start()
                interaction_timing["scheduled_timers"].append(timer)

def check_and_skip_attempted_question(driver):
    try:
        check_icon = driver.find_element(By.CSS_SELECTOR, 'div.XpcpKLY2T7 svg[data-icon="check"]')
        if check_icon:
            print("Question attempted, skipping")
            continue_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
            if continue_button.text == "Continue":
                driver.execute_script("arguments[0].click();", continue_button)
                print("Clicked Continue")
                time.sleep(1)
                return True
        return False
    except Exception as e:
        print(f"Error checking attempted status: {str(e)}")
        return False

def process_interaction(driver, interaction_time=None):
    print(f"\n=== Interaction at {interaction_time}s reached ===")
    
    if interaction_time:
        current_time = driver.execute_script("return document.querySelector('video').currentTime;")
        playback_rate = driver.execute_script("return document.querySelector('video').playbackRate;")
        print(f"Video time: {current_time:.2f}s, Expected: {interaction_time}s, Rate: {playback_rate}x")
    
    time.sleep(5)
    if check_and_skip_attempted_question(driver):
        reschedule_remaining_interactions(driver)
        return
    
    try:
        # Check for pagination or "Next question" button to determine multiple interactions
        pagination_elements = driver.find_elements(By.CSS_SELECTOR, "div.pagination-indicator")
        next_question_button = driver.find_elements(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
        is_multiple = len(pagination_elements) > 0 or (next_question_button and next_question_button[0].text == "Next question")
        
        if is_multiple:
            if pagination_elements:
                process_multiple_interactions(driver, pagination_elements)
            else:
                # Handle "Next question" as multiple interaction
                print("Detected 'Next question' - Treating as multiple interaction")
                extracted_data = extract_question_and_options(driver)
                if extracted_data:
                    answer = answer_question_with_fallback(extracted_data)
                    select_answer_in_ui(driver, answer, is_multiple=True)
        else:
            process_single_interaction(driver)
            
    except Exception as e:
        print(f"Error processing interaction: {str(e)}")
        driver.save_screenshot("interaction_error.png")
        try:
            extracted_data = extract_question_and_options(driver)
            if extracted_data:
                answer = answer_question_with_fallback(extracted_data)
                select_answer_in_ui(driver, answer)
        except:
            print("Failed to salvage interaction")

def reschedule_remaining_interactions(driver):
    interaction_times = extract_interaction_times(driver)
    if interaction_times:
        schedule_interactions(driver, interaction_times)

def process_multiple_interactions(driver, pagination_elements):
    pagination_text = pagination_elements[0].text
    total_interactions = int(pagination_text.split("of")[1].strip())
    print(f"Processing {total_interactions} interactions")
    
    for i in range(total_interactions):
        pagination_elements = driver.find_elements(By.CSS_SELECTOR, "div.pagination-indicator")
        if pagination_elements:
            current = int(pagination_elements[0].text.split("of")[0].strip())
            print(f"\nProcessing interaction {current} of {total_interactions}")
            extracted_data = extract_question_and_options(driver)
            if extracted_data:
                answer = answer_question_with_fallback(extracted_data)
                select_answer_in_ui(driver, answer, is_multiple=True)
        else:
            break

def process_single_interaction(driver):
    print("Processing single interaction")
    extracted_data = extract_question_and_options(driver)
    if extracted_data:
        answer = answer_question_with_fallback(extracted_data)
        select_answer_in_ui(driver, answer, is_multiple=False)
    else:
        print("Failed to extract question")
        driver.save_screenshot("interaction_question_error.png")

def extract_question_and_options(driver):
    try:
        os.makedirs("Question", exist_ok=True)
        
        # Take a screenshot for debugging
        driver.save_screenshot("extraction_attempt.png")
        print( "sleeping for")
        # Add a small fixed delay to ensure page has loaded
        time.sleep(5)
        print("Extraction attempt")
        # Direct extraction of question
        print("Extraction first time ")
        question_elements = driver.find_elements(By.CSS_SELECTOR, 'section.qtU_WlqWdC p')
        
        if not question_elements:
            # Try alternative selectors if the first one fails
            print("Extraction second time " )
            question_elements = driver.find_elements(By.CSS_SELECTOR, 'div.qtU_WlqWdC p')
        
        if not question_elements:
            print("No question elements found")
            return None
            
        question = question_elements[0].text.strip()
        print(f"Found question: {question}")
        
        # Direct extraction of options
        options_elements = driver.find_elements(By.CSS_SELECTOR, 'section.xpe9TO2_Hw ul.S22KF9HiqC li label span p')
        
        if not options_elements:
            # Try alternative selectors if the first one fails
            options_elements = driver.find_elements(By.CSS_SELECTOR, 'ul.S22KF9HiqC li label span p')
        
        if not options_elements:
            print("No option elements found")
            return None
            
        options = [option.text.strip() for option in options_elements if option.text.strip()]
        print(f"Found {len(options)} options")
        
        if question and options:
            output = {"Question": question}
            for i, option in enumerate(options, 1):
                output[f"Option {i}"] = option
            
            file_name = f"Question/{sanitize_filename(question)}.json"
            with open(file_name, "w", encoding="utf-8") as json_file:
                json.dump(output, json_file, ensure_ascii=False, indent=4)
            
            print(f"Extracted question saved to {file_name}")
            return output
        
        print("Question or options empty after extraction")
        return None
        
    except Exception as e:
        print(f"Error extracting question/options: {str(e)}")
        driver.save_screenshot("extraction_error.png")
        return None
    
        
    except TimeoutException:
        print("Timeout waiting for question/options to load.")
        driver.save_screenshot("question_extraction_timeout.png")
        # Fallback: Retry once after a short delay
        try:
            time.sleep(2)  # Brief pause for UI to settle
            question_element = driver.find_element(By.CSS_SELECTOR, 'section.qtU_WlqWdC p')
            question = question_element.text.strip()
            options_elements = driver.find_elements(By.CSS_SELECTOR, 'section.xpe9TO2_Hw ul.S22KF9HiqC li label span p')
            options = [option.text.strip() for option in options_elements if option.text.strip()]
            
            if question and options:
                output = {"Question": question}
                for i, option in enumerate(options, 1):
                    output[f"Option {i}"] = option
                
                file_name = f"Question/{sanitize_filename(question)}.json"
                with open(file_name, "w", encoding="utf-8") as json_file:
                    json.dump(output, json_file, ensure_ascii=False, indent=4)
                
                print(f"Fallback: Extracted question saved to {file_name}")
                return output
            print("Fallback failed: No question/options found.")
            return None
        except Exception as e:
            print(f"Fallback error: {str(e)}")
            return None
    except Exception as e:
        print(f"Unexpected error extracting question/options: {str(e)}")
        driver.save_screenshot("question_extraction_error.png")
        return None

def answer_question_with_fallback(question_data):
    os.makedirs("answer", exist_ok=True)
    
    question = question_data["Question"]
    file_name = f"answer/{sanitize_filename(question)}.json"
    
    # Check if the answer is already stored
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as json_file:
            stored_answer_data = json.load(json_file)
            if "Final Answer" in stored_answer_data:
                print(f"Using stored answer for question: {question}")
                return stored_answer_data["Final Answer"]

    # If not stored, proceed with LLM-based answering
    llm_manager = LLMManager()
    llm_instances = llm_manager.setup_llm_with_fallback()
    
    options = [value for key, value in question_data.items() if key.startswith("Option")]
    formatted_input = f"Question: {question}\nOptions:\n" + "\n".join(options) + "\nAnswer based only on the options. Output only the answer."
    
    final_answer = llm_manager.invoke_with_fallback(llm_instances, llm_manager.DEFAULT_FALLBACK_ORDER, formatted_input)
    question_data["Final Answer"] = final_answer
    
    # Save the answer for future use
    with open(file_name, "w", encoding="utf-8") as json_file:
        json.dump(question_data, json_file, ensure_ascii=False, indent=4)
    
    print(f"Answer saved in {file_name}")
    return final_answer

def select_answer_in_ui(driver, answer, is_multiple=False):
    try:
        option_elements = driver.find_elements(By.CSS_SELECTOR, 'section.xpe9TO2_Hw ul.S22KF9HiqC li label')
        for element in option_elements:
            option_text = element.find_element(By.CSS_SELECTOR, 'span p').text.strip()
            if option_text == answer:
                input_id = element.get_attribute('for')
                checkbox = driver.find_element(By.ID, input_id)
                driver.execute_script("arguments[0].click();", checkbox)
                print(f"Selected answer: {answer}")
                time.sleep(a)
                
                try:
                    action_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
                    button_text = action_button.text
                    if button_text == "Submit":
                        driver.execute_script("arguments[0].click();", action_button)
                        print("Clicked Submit")
                        time.sleep(5)
                        try:
                            continue_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
                            if continue_button.text == "Continue":
                                driver.execute_script("arguments[0].click();", continue_button)
                                print("Clicked Continue")
                        except:
                            print("Continue button not found")
                        reschedule_remaining_interactions(driver)
                        return True
                    elif button_text == "Next question" and is_multiple:
                        driver.execute_script("arguments[0].click();", action_button)
                        print("Clicked Next question - Continuing multiple interaction")
                        time.sleep(1)  # Brief initial delay
                        try:
                            # Wait for the question to be present and interactable
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'section.qtU_WlqWdC p'))
                            )
                            print("Next question UI loaded")
                            extracted_data = extract_question_and_options(driver)
                            if extracted_data:
                                answer = answer_question_with_fallback(extracted_data)
                                select_answer_in_ui(driver, answer, is_multiple=True)
                                return True
                            else:
                                print("Failed to extract next question")
                                driver.save_screenshot("next_question_failed.png")
                                return False
                        except TimeoutException:
                            print("Timeout waiting for next question to load")
                            driver.save_screenshot("next_question_timeout.png")
                            return False
                except Exception as e:
                    print(f"Error with button action: {str(e)}")
                    return False
                
        print(f"Could not find option: {answer}")
        driver.save_screenshot("answer_selection_error.png")
        return False
        
    except Exception as e:
        print(f"Error selecting answer: {str(e)}")
        driver.save_screenshot("answer_selection_error.png")
        return False