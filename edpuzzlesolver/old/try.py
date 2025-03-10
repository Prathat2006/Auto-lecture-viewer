import cv2
import numpy as np
import pytesseract
import mss
from PIL import Image
import sys
import time

# Set the path to the Tesseract executable (modify this path according to your installation)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def capture_screen(monitor_index=1):
    """
    Capture the full screen of the specified monitor and return a PIL Image.
    """
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[monitor_index]
            screenshot = sct.grab(monitor)
            img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)
            return img
    except Exception as e:
        print(f"Error capturing screen: {e}")
        sys.exit(1)

def preprocess_image(img_cv):
    """
    Convert image to grayscale and apply thresholding for better OCR results.
    """
    gray = cv2.cvtColor(img_cv, cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def find_text_and_capture(target_text, padding=10):
    """
    Capture the screen, preprocess the image, use OCR to locate target_text,
    and save a cropped image around it.
    """
    print("Capturing screen...")
    img_pil = capture_screen()
    img_cv = np.array(img_pil)
    
    print("Preprocessing image for OCR...")
    processed_img = preprocess_image(img_cv)
    
    print("Running OCR...")
    custom_config = r'--oem 3 --psm 6'
    try:
        data = pytesseract.image_to_data(processed_img, config=custom_config, output_type=pytesseract.Output.DICT)
        extracted_text = pytesseract.image_to_string(processed_img, config=custom_config)
        print("Extracted Text from Screen:\n", extracted_text)
    except Exception as e:
        print(f"OCR processing error: {e}")
        return None

    found = False
    for i in range(len(data['text'])):
        if data['text'][i].strip() and target_text.lower() in data['text'][i].lower():
            x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
            x_start, y_start = max(x - padding, 0), max(y - padding, 0)
            x_end, y_end = min(x + w + padding, img_cv.shape[1]), min(y + h + padding, img_cv.shape[0])
            
            cropped_img = img_cv[y_start:y_end, x_start:x_end]
            output_path = f"screenshot_{target_text}.png"
            cv2.imwrite(output_path, cv2.cvtColor(cropped_img, cv2.COLOR_RGB2BGR))
            print(f"Screenshot saved as {output_path}")
            
            # Draw rectangle around detected text for debugging
            cv2.rectangle(img_cv, (x_start, y_start), (x_end, y_end), (0, 255, 0), 2)
            found = True

    cv2.imshow("Detected Text", img_cv)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    if not found:
        print(f"Text '{target_text}' not found on the screen.")
        return None

if __name__ == "__main__":
    target_text = input("Enter the text to search for: ")
    time.sleep(5)
    find_text_and_capture(target_text)
