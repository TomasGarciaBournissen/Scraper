from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
import csv, time
import os
import re

service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)

rows = []

def filterprice(item):
    texto = item

    
    coincidencia = re.search(r"x lt\.\:\s*(\$[\d\.,]+)", texto)

    if coincidencia:
        precio = coincidencia.group(1)
        print("Precio encontrado:", precio)
        return precio
    else:
        print("No se encontró el precio.")



urls = [
    "https://www.jumbo.com.ar/pantene?_q=pantene&map=ft",
    
    
    
]

for i in range (len(urls)):
    driver.get(urls[i])



    total_height = driver.execute_script("return document.body.scrollHeight")

    # Calculate one-third
    one_third = total_height / 3

    # Scroll down by one-third of the page
    



   
   
    time.sleep(1)
    index = 0
    while True:
        file_exists = os.path.isfile('preciosV2.csv') and os.stat('preciosV2.csv').st_size > 0

        

        

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[.//span[text()='Ver Producto']]")))
        time.sleep(1)
        driver.execute_script(f"window.scrollTo(0, {-total_height});")
        time.sleep(1)
        driver.execute_script(f"window.scrollTo(0, {one_third*1.2});")
        time.sleep(1)
        product_buttons = driver.find_elements(By.XPATH, "//button[.//span[text()='Ver Producto']]")

        
        total = len(product_buttons)
        print(f"Total products found: {total}")
        if index >= total:
            print("All buttons processed, exiting loop.")
            break


    
        print(f"Processing product {index+1}/{len(product_buttons)}")
        button = product_buttons[index]
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", button)
        try:

           
            
           
            
            button.click()
            
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'vtex-store-components-3-x-productBrand')]")))
            time.sleep(1)
            brandName = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-store-components-3-x-productBrandName')]").text

            name = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-store-components-3-x-productBrand')]").text
        
            price = driver.find_element(By.XPATH, "//div[contains(@class, 'vtex-price-format-gallery')]").text
            
            pl = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-custom-unit-price')]").text
            pricepl = filterprice(pl)

            sku = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-product-identifier-0-x-product-identifier__value')]").text
            

            rows.append([brandName, name, price, pricepl, sku])
            time.sleep(1)
            driver.back()



            
            with open('preciosV2.csv', mode='a', newline='')as f:
                writer = csv.DictWriter(f, fieldnames=['brand','name', 'price', 'PPL', 'SKU'])
            

                if not file_exists:
                    writer.writeheader()
                writer.writerow({'brand': brandName,'name': name, 'price': price, 'PPL': pricepl, 'SKU': sku})
                

            print(f"BN: {brandName}, Nombre: {name}, Precio: {price}, PPL: {pricepl}, SKU: {sku}")
            print("product loaded successfully")

        except Exception as e:
            print(f"Error al obtener datos del producto: {e}")
            continue
        print(f"Processed product {index+1}/{len(product_buttons)}")
        index += 1

for row in rows:
    print(row)



