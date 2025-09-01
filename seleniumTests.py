from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import csv, time
import os

# Initialize the Chrome driver
service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)


# Obtain price \
link = "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio"
driver.get(link)
time.sleep(1)
search_box = WebDriverWait(driver, 10).until(
    EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='¿Qué querés comprar hoy?']"))
)
search_box.send_keys("arroz")
search_box.send_keys(Keys.RETURN)
time.sleep	(3)


driver.quit()