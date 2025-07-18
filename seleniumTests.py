from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv, time
import os

# Initialize the Chrome driver
service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)


# Obtain price \
link = "https://www.cotodigital.com.ar/sitios/cdigi/productos/aromatizante-para-ropa-april-fresh-downy-345g/_/R-00586869-00586869-200?Dy=1&idSucursal=200"
driver.get(link)
time.sleep(1)

brand= driver.find_element(By.XPATH, "//td[span[normalize-space()='MARCA']]").text
print(f"Brand: {brand}")
driver.quit()