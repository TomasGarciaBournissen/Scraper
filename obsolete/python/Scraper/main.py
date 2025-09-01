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
link = "https://www.cotodigital.com.ar/sitios/cdigi/categoria/brand-comfort/_/N-1ow618q?Dy=1&Nf=product.startDate%7CLTEQ%201.7497728E12%7C%7Cproduct.endDate%7CGTEQ%201.7497728E12&Nr=AND(product.sDisp_200:1004,product.language:espa%C3%B1ol,OR(product.siteId:CotoDigital))&assemblerContentCollection=%2Fcontent%2FShared%2FAuto-Suggest%20Panels"
driver.get(link)
time.sleep(6)

product_divs = driver.find_elements(By.CLASS_NAME, "centro-precios")

file_exists = os.path.isfile('precios.csv') and os.stat('precios.csv').st_size > 0

with open('precios.csv', mode='a', newline='')as f:
    writer = csv.DictWriter(f, fieldnames=['name', 'price', 'PPL'])
    

    if not file_exists:
        writer.writeheader()
    for div in product_divs:
        try:
            
            nombre = div.find_element(By.CSS_SELECTOR, "h3.nombre-producto" ).text
            precio = div.find_element(By.CSS_SELECTOR, "h4.card-title").text  
            ppl = pl = div.find_element(By.CSS_SELECTOR, "small.card-text").text  
               
        except Exception as e:
            print(f"Error al obtener datos del producto: {e}")
            continue    
        writer.writerow({'name': nombre, 'price': precio, 'PPL': ppl})
        print(f"Guardado  Nombre: {nombre}, Precio: {precio}")
        # Write the data to the CSV file
    
    
driver.quit()