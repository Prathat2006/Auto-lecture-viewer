import os
import json
import time
import re
from threading import Timer, Lock
from lmsusingselenium.driver import setup_driver
from selenium import webdriver
from selenium.webdriver.common.by import By
from edpuzzlesolver.llminit import LLMManager

# Track cumulative interaction timing adjustments
interaction_timing = {
    "cumulative_delay": 0,  # Total accumulated delay from previous interactions
    "timing_lock": Lock()   # Lock for thread-safe updates
}

a = 15
def sanitize_filename(name):
    """Removes invalid filename characters."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', name[:50])

def extract_interaction_times(driver):
    """
    Extracts interaction time points from the video player timeline and schedules
    the question extraction and answering functions to run at those times.
    Handles both single and multiple interaction markers.
    Adjusts timing for video playback speed and cumulative processing delays.
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        List of interaction times in seconds
    """
    import re
    import time
    from threading import Timer
    
    try:
        # Wait for video player and interaction markers to load
        time.sleep(3)
        
        # Find the interaction markers container
        interaction_container = driver.find_element(By.CSS_SELECTOR, "div.OLRXd3vFHv")
        
        # Find all interaction markers (both single and multiple)
        interaction_markers = interaction_container.find_elements(
            By.CSS_SELECTOR, 
            "div[role='button'][aria-label^='Interaction at'], div[role='button'][aria-label^='Multiple interactions at']"
        )
        
        if not interaction_markers:
            print("No interaction markers found in the video.")
            return []
            
        interaction_times = []
        
        # Extract time from each marker
        for marker in interaction_markers:
            aria_label = marker.get_attribute('aria-label')
            
            # Handle single interaction
            single_match = re.search(r'Interaction at (\d+) seconds', aria_label)
            # Handle multiple interactions
            multiple_match = re.search(r'Multiple interactions at (\d+) seconds', aria_label)
            
            if single_match:
                seconds = int(single_match.group(1))
                interaction_times.append(seconds)
                print(f"Found single interaction at {seconds} seconds")
            elif multiple_match:
                seconds = int(multiple_match.group(1))
                interaction_times.append(seconds)
                print(f"Found multiple interactions at {seconds} seconds")
        
        if not interaction_times:
            print("Failed to extract interaction times from markers.")
            return []
            
        # Sort interaction times in ascending order
        interaction_times.sort()
        
        print(f"Extracted interaction times: {interaction_times}")
        
        # Get current video time and playback rate
        current_time_script = "return document.querySelector('video').currentTime;"
        current_time = int(driver.execute_script(current_time_script))
        
        playback_rate_script = "return document.querySelector('video').playbackRate;"
        playback_rate = driver.execute_script(playback_rate_script)
        print(f"Current video playback rate: {playback_rate}x")
        
        # Get the current cumulative delay
        with interaction_timing["timing_lock"]:
            cumulative_delay = interaction_timing["cumulative_delay"]
            
        if cumulative_delay > 0:
            print(f"Current cumulative delay: {cumulative_delay:.2f} seconds")
        
        # Schedule functions to run at each interaction time
        for idx, interaction_time in enumerate(interaction_times):
            if interaction_time > current_time:
                # Base wait time (without adjustments)
                base_wait_seconds = (interaction_time - current_time) / playback_rate
                
                # Adjust wait time by ADDING the cumulative delay (since the video progress bar stops during interactions)
                # This extends our wait time to account for the paused video during previous interactions
                adjusted_wait = base_wait_seconds + (cumulative_delay / playback_rate)
                
                print(f"Scheduling interaction at {interaction_time} seconds:")
                print(f"  - Base wait: {base_wait_seconds:.2f}s")
                print(f"  - Adjusted wait: {adjusted_wait:.2f}s (includes {cumulative_delay:.2f}s delay at {playback_rate}x speed)")
                
                # Create a timer that will run the extraction and answering functions
                timer = Timer(adjusted_wait, process_interaction, args=[driver, interaction_time])
                timer.daemon = True  # Allow the timer to be terminated when the main program exits
                timer.start()
        
        return interaction_times
        
    except Exception as e:
        print(f"Error extracting interaction times: {str(e)}")
        driver.save_screenshot("interaction_extraction_error.png")
        return []
def check_and_skip_attempted_question(driver):
    """
    Checks if a multiple-choice question is attempted by looking for the check icon.
    If attempted, clicks 'Continue' directly; otherwise, returns False to proceed with answering.
    
    Args:
        driver: Selenium WebDriver instance
    
    Returns:
        bool: True if question was attempted and skipped, False otherwise
    """
    try:
        # Look for the check icon within the specified div
        check_icon = driver.find_element(By.CSS_SELECTOR, 'div.XpcpKLY2T7 svg[data-icon="check"]')
        
        # If the check icon exists, the question is attempted
        if check_icon:
            print("Question already attempted, skipping to Continue")
            
            # Find and click the Continue button
            continue_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
            if continue_button.text == "Continue":
                driver.execute_script("arguments[0].click();", continue_button)
                print("Clicked Continue, video should resume")
                time.sleep(1)
                return True
            else:
                print("Continue button not found")
                return False
                
        else:
            print("No check icon found, question not attempted")
            return False
            
    except Exception as e:
        print(f"Error checking attempted status: {str(e)}")
        return False

def update_interaction_timing(start_time):
    """
    Updates the cumulative delay based on how long this interaction took.
    Thread-safe implementation using a lock.
    
    Args:
        start_time: Time when interaction processing started
        
    Returns:
        float: Time elapsed for this interaction
    """
    elapsed = time.time() - start_time
    
    with interaction_timing["timing_lock"]:
        # Add this interaction's time to the cumulative delay
        interaction_timing["cumulative_delay"] += elapsed
        total_delay = interaction_timing["cumulative_delay"]
        
    print(f"Interaction completed in {elapsed:.2f} seconds")
    print(f"Cumulative delay is now {total_delay:.2f} seconds")
    
    return elapsed

# Integrate timing tracking into process_interaction
def process_interaction(driver, interaction_time=None):
    start_time = time.time()
    current_time = int(time.time())
    print(f"\n=== Interaction point reached at {current_time} (timestamp: {time.time():.2f}) ===")
    
    if interaction_time:
        playback_rate_script = "return document.querySelector('video').playbackRate;"
        playback_rate = driver.execute_script(playback_rate_script)
        current_time_script = "return document.querySelector('video').currentTime;"
        video_time = driver.execute_script(current_time_script)
        print(f"Video current time: {video_time:.2f}s, Expected interaction time: {interaction_time}s, Playback rate: {playback_rate}x")
    
    time.sleep(5)
    
    # Check if question is already attempted
    if check_and_skip_attempted_question(driver):
        # Still update timing even if we skipped
        update_interaction_timing(start_time)
        return  # Skip further processing if attempted
    
    # Proceed with normal question processing if not attempted
    try:
        pagination_elements = driver.find_elements(By.CSS_SELECTOR, "div.pagination-indicator")
        is_multiple = len(pagination_elements) > 0
        
        if is_multiple:
            print("Multiple interactions detected.")
            pagination_text = pagination_elements[0].text
            # Example: "1 of 3"
            total_interactions = int(pagination_text.split("of")[1].strip())
            current_interaction = int(pagination_text.split("of")[0].strip())
            print(f"Processing interaction {current_interaction} of {total_interactions}")
            
            # Process all interactions in sequence
            interactions_processed = 0
            max_attempts = total_interactions * 2  # Safety to prevent infinite loops
            attempts = 0
            
            while interactions_processed < total_interactions and attempts < max_attempts:
                attempts += 1
                pagination_elements = driver.find_elements(By.CSS_SELECTOR, "div.pagination-indicator")
                if pagination_elements:
                    pagination_text = pagination_elements[0].text
                    current_interaction = int(pagination_text.split("of")[0].strip())
                    
                    print(f"\nProcessing interaction {current_interaction} of {total_interactions}")
                    extracted_data = extract_question_and_options(driver)
                    if extracted_data:
                        print(f"Question {current_interaction} extracted successfully. Generating and selecting answer...")
                        answer = answer_question_with_fallback(extracted_data)
                        select_answer_in_ui(driver, answer)
                        interactions_processed += 1
                    
                    # Check if we've processed all interactions
                    if interactions_processed >= total_interactions:
                        break
                    
                    # Try to find and click the "Next" button if we haven't processed all interactions
                    try:
                        next_button = driver.find_element(By.CSS_SELECTOR, "div.n_fDEjdOhe button span.vRiXkQIxXS")
                        driver.execute_script("arguments[0].click();", next_button)
                        print("Clicked Next button to move to next question")
                        time.sleep(2)
                    except Exception as e:
                        print(f"Could not find Next button: {str(e)}")
                        # If we can't find Next button, check if we have a Continue button instead
                        try:
                            continue_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
                            if continue_button.text == "Continue":
                                driver.execute_script("arguments[0].click();", continue_button)
                                print("Clicked Continue, interactions complete")
                                break
                        except:
                            print("Neither Next nor Continue button found")
                else:
                    print("Pagination elements no longer found")
                    break
            
            print(f"=== Multiple interactions processing complete: {interactions_processed}/{total_interactions} ===\n")
        else:
            print("Processing single interaction.")
            extracted_data = extract_question_and_options(driver)
            if extracted_data:
                print("Question extracted successfully. Generating and selecting answer...")
                answer = answer_question_with_fallback(extracted_data)
                select_answer_in_ui(driver, answer)
                print("=== Interaction processing complete ===\n")
            else:
                print("Failed to extract question at interaction point.")
                driver.save_screenshot("interaction_question_error.png")
                
    except Exception as e:
        print(f"Error processing interaction: {str(e)}")
        driver.save_screenshot("interaction_error.png")
        # Attempt to salvage the situation
        try:
            extracted_data = extract_question_and_options(driver)
            if extracted_data:
                answer = answer_question_with_fallback(extracted_data)
                select_answer_in_ui(driver, answer)
        except:
            print("Failed to salvage the interaction")
    
    # Update timing statistics before returning
    elapsed_time = update_interaction_timing(start_time)
    return elapsed_time

def extract_question_and_options(driver):
    """
    Extract question and options from the current LMS page using the provided driver,
    and save the extracted data into a JSON file inside the 'Question' folder.
    """
    try:
        # Ensure the 'Question' folder exists
        os.makedirs("Question", exist_ok=True)

        attempts = 8  # Number of attempts
        for attempt in range(attempts):
            # Wait for elements to load
            time.sleep(5 if attempt == 0 else 7)  # Wait 5 seconds initially, then 7 seconds if retrying
            
            try:
                # Extract the question
                question_element = driver.find_element(By.CSS_SELECTOR, 'section.qtU_WlqWdC p')
                question = question_element.text.strip()
                
                # Extract all options
                options_elements = driver.find_elements(By.CSS_SELECTOR, 'section.xpe9TO2_Hw ul.S22KF9HiqC li label span p')
                options = [option.text.strip() for option in options_elements]
                
                if question and options:
                    # Prepare the output in the required format
                    output = {"Question": question}
                    for i, option in enumerate(options, 1):
                        output[f"Option {i}"] = option
                    
                    # Generate a sanitized filename
                    file_name = f"Question/{sanitize_filename(question)}.json"
                    
                    # Save the output to a JSON file
                    with open(file_name, "w", encoding="utf-8") as json_file:
                        json.dump(output, json_file, ensure_ascii=False, indent=4)
                    
                    print(f"Extracted question saved to {file_name}")
                    return output
                
            except Exception as e:
                print(f"Attempt {attempt + 1}: Error extracting question and options: {str(e)}")
                if attempt == attempts - 1:
                    print("Final attempt failed. Moving on...")
                    return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def answer_question_with_fallback(question_data):
    """
    Uses LLM fallback system to answer the given question based on provided options.
    Stores the final output in a JSON file inside the 'answer' folder.
    """
    # Ensure the 'answer' folder exists
    os.makedirs("answer", exist_ok=True)
    
    # Initialize LLM Manager and setup fallback LLMs
    llm_manager = LLMManager()
    llm_instances = llm_manager.setup_llm_with_fallback()
    
    # Prepare input for LLM
    question = question_data["Question"]
    options = [value for key, value in question_data.items() if key.startswith("Option")]
    formatted_input = f"Question: {question}\nOptions:\n" + "\n".join(options) + "\nAnswer based only on the options. Output only the answer."
    
    # Invoke the LLM with fallback system
    final_answer = llm_manager.invoke_with_fallback(llm_instances, llm_manager.DEFAULT_FALLBACK_ORDER, formatted_input)
    
    # Append the final answer to the JSON data
    question_data["Final Answer"] = final_answer
    
    # Generate a sanitized filename
    file_name = f"answer/{sanitize_filename(question)}.json"
    
    # Save to JSON file
    with open(file_name, "w", encoding="utf-8") as json_file:
        json.dump(question_data, json_file, ensure_ascii=False, indent=4)
    
    print(f"Answer saved in {file_name}")
    return final_answer

def select_answer_in_ui(driver, answer):
    try:
        # Find all option elements
        option_elements = driver.find_elements(By.CSS_SELECTOR, 'section.xpe9TO2_Hw ul.S22KF9HiqC li label')
        for element in option_elements:
            option_text = element.find_element(By.CSS_SELECTOR, 'span p').text.strip()
            if option_text == answer:
                input_id = element.get_attribute('for')
                checkbox = driver.find_element(By.ID, input_id)
                driver.execute_script("arguments[0].click();", checkbox)
                print(f"Selected answer: {answer}")
                time.sleep(a)  # Brief wait for selection
                
                # Try to submit the answer
                try:
                    submit_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
                    if submit_button.text == "Submit":
                        driver.execute_script("arguments[0].click();", submit_button)
                        print("Clicked Submit button")
                        time.sleep(5)  # Wait for UI to update
                        
                        # Check if submission worked by looking for Continue button
                        try:
                            continue_button = driver.find_element(By.CSS_SELECTOR, 'div.n_fDEjdOhe button span.vRiXkQIxXS')
                            if continue_button.text == "Continue":
                                driver.execute_script("arguments[0].click();", continue_button)
                                print("Clicked Continue, video should resume")
                                return
                        except Exception:
                            print("Continue button not found, submission may have failed")
                    else:
                        print("Submit button text was not 'Submit', found: " + submit_button.text)
                except Exception as e:
                    print(f"Error with submit button: {str(e)}")
                
                # If we're here, the submit button didn't work or we couldn't find the continue button
                # Try to find and click the Next button for multiple interactions
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='Next']")
                    driver.execute_script("arguments[0].click();", next_button)
                    print("Clicked Next button to move to next question")
                    time.sleep(2)
                except Exception as e:
                    print(f"Could not find Next button: {str(e)}")
                
                return
        
        print(f"Could not find option matching answer: {answer}")
        driver.save_screenshot("answer_selection_error.png")
        
    except Exception as e:
        print(f"Error selecting answer in UI: {str(e)}")
        driver.save_screenshot("answer_selection_error.png")