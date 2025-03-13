from lmsusingselenium.lms import login_to_lms,select_and_navigate_to_subject, navigate_to_self_paced_learning, select_and_open_lecture,select_and_open_module,select_and_open_week,set_video_speed,play_video
from lmsusingselenium.whynot import extract_question_and_options,answer_question_with_fallback ,extract_interaction_times
import time
import traceback

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
            
            # First, select and open a module
            selected_module = select_and_open_module(driver)
            if not selected_module:
                print("Failed to select and open a module. Exiting.")
                return
            
            # After opening the module, select and open a week
            time.sleep(2)  # Wait for module content to load
            selected_week = select_and_open_week(driver)
            if not selected_week:
                print("Failed to select and open a week. Exiting.")
                return
            
            # After opening the week, select and open a lecture
            time.sleep(2)  # Wait for week content to load
            selected_lecture = select_and_open_lecture(driver)

            if not selected_lecture:
                print("Failed to select and open a lecture. Exiting.")
                return
                
            print(f"\nSuccessfully navigated to {selected_module} > {selected_week} > {selected_lecture}")
            time.sleep(5) # Wait for lecture to load  
            play_video(driver)
            
            # Extract interaction times and schedule processes
            interaction_times = extract_interaction_times(driver)
            
            if interaction_times:
                print(f"Found {len(interaction_times)} interaction points. Automation will process them as they occur.")
                
                # Keep the script running until all interactions are processed  and..
                max_time = max(interaction_times) + 30  # Add 30 seconds buffer
                print(f"Script will run for approximately {max_time} seconds")
                
                # Sleep until all interactions should be processed
                time.sleep(max_time)
            else:
                print("No interaction points found. Video will play without automation.")
                # Default wait time if no interaction points are found
                time.sleep(180)
                
        except Exception as e:
            print(f"An error occurred during automation: {str(e)}")
            traceback.print_exc()
            driver.save_screenshot("automation_error.png")
    else:
        print("Login failed. Cannot proceed with navigation.")

if __name__ == "__main__":
    main()