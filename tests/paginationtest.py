from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Remote
from concurrent.futures import ThreadPoolExecutor
import csv,time,os,re,threading

# Replace with your actual Grid hub URL
GRID_URL = "http://localhost:4444/wd/hub"

# The page that contains the "next" button
TARGET_URL = "https://www.jumbo.com.ar/dove?_q=dove&map=ft&page=1"  # Replace with the actual site you're testing

# Define desired capabilities (example for Chrome)
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

# Connect to Selenium Grid
driver = webdriver.Remote(
    command_executor=GRID_URL,
    options=options
)

# Open the page

def element_exists(driver,xpath):
    try:

        WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return True
    except TimeoutException:
        return False
def obtener_total_paginas(driver):
    try:
        botones = driver.find_elements(By.XPATH, "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]")

        if element_exists(driver, "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]"):
            print(" Botones encontrados")


        nums = [int(b.text.strip()) for b in botones if b.text.strip().isdigit()]
        print(f" Botones encontrados: {len(botones)}")
        return max(nums) if nums else 1
        
    except:
        return 1

    
driver.get(TARGET_URL)
time.sleep(5)  # Wait for the page to load
total_paginas = obtener_total_paginas(driver)
print(f" Total de páginas: {total_paginas} para la URL dove")
driver.quit()