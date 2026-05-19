import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import requests
from datetime import datetime, timezone
class BaseScraper:

    def __init__(self):
        # 1. Setup options (Optional: run in headless mode without a GUI)
        options = webdriver.ChromeOptions()
        # options.add_argument("--headless") 
        options.add_argument("--start-maximized")

        # 2. Initialize the driver
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        
        self.today = datetime.now(timezone.utc)
        
    def close(self):
        self.driver.quit()

        