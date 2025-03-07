import pyautogui
import time


def openlana():
    pyautogui.scroll(-200) 
    no=pyautogui.locateCenterOnScreen(r"D:\\project\\miscellaneous\\Lecture_download\\buttons\\lana.png",confidence=0.5)
    pyautogui.click(no,clicks=2,interval=1)
    time.sleep(5)
