from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv, time, os, re

# Configuración del driver
service = Service(executable_path="chromedriver.exe")
driver = webdriver.Chrome(service=service)

# Lista para guardar los productos
rows = []

# Función para extraer precio por litro
def filterprice(item):
    m = re.search(r"x lt\.\:\s*(\$[\d\.,]+)", item)
    return m.group(1) if m else ""

# URLs a scrapear
urls = [
    "https://www.jumbo.com.ar/pantene?_q=pantene&map=ft",
    "https://www.jumbo.com.ar/downy?_q=downy&map=ft",
    "https://www.jumbo.com.ar/elvive?_q=ELVIVE&map=ft",
    "https://www.jumbo.com.ar/comfort%20suavizante?_q=COMFORT%20suavizante&map=ft",
]

# Preparamos CSV
file_exists = os.path.isfile('preciosV2.csv') and os.stat('preciosV2.csv').st_size > 0
with open('preciosV2.csv', mode='a', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=['brand', 'name', 'price', 'PPL', 'SKU'])
    if not file_exists:
        writer.writeheader()

    for url in urls:
        driver.get(url)
        time.sleep(1)

        # Si hay múltiples páginas, hacemos un bucle
        while True:
            # Scroll para intentar cargar productos (ajustar si es necesario)
            total_h = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script(f"window.scrollTo(0, {total_h / 2.7});")
            time.sleep(2)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//button[.//span[text()='Ver Producto']]"))
            )

            product_buttons = driver.find_elements(By.XPATH, "//button[.//span[text()='Ver Producto']]")
            print(f"Pág. actual: botones encontrados = {len(product_buttons)}")

            for index in range(len(product_buttons)):
                try:
                    product_buttons = driver.find_elements(By.XPATH, "//button[.//span[text()='Ver Producto']]")
                    button = product_buttons[index]
                    parent_link = button.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
                    original_window = driver.current_window_handle
                    driver.execute_script("window.open(arguments[0]);", parent_link)
                    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
                    new_win = [w for w in driver.window_handles if w != original_window][0]
                    driver.switch_to.window(new_win)
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'vtex-store-components-3-x-productBrandName')]"))
                    )
                    time.sleep(1)

                    brand = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-store-components-3-x-productBrandName')]").text
                    name = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-store-components-3-x-productBrand')]").text
                    price = driver.find_element(By.XPATH, "//div[contains(@class, 'vtex-price-format-gallery')]").text
                    pl_text = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-custom-unit-price')]").text
                    ppl = filterprice(pl_text)
                    sku = driver.find_element(By.XPATH, "//span[contains(@class, 'vtex-product-identifier-0-x-product-identifier__value')]").text

                    writer.writerow({'brand': brand, 'name': name, 'price': price, 'PPL': ppl, 'SKU': sku})
                    rows.append([brand, name, price, ppl, sku])
                    print(f"{index+1}/{len(product_buttons)}: {brand} | {name} | {price} | {ppl} | {sku}")

                    driver.close()
                    driver.switch_to.window(original_window)
                    time.sleep(1)

                except Exception as e:
                    print(f"Error producto {index+1}: {e}")
                    try:
                        driver.close()
                        driver.switch_to.window(original_window)
                    except: pass
                    continue

            # verificar si hay más páginas
            try:
                next_btn = driver.find_element(
                    By.XPATH,
                    "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='2']"
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", next_btn)
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='2']"
                )))
                next_btn.click()
                print(" moviendo a la página 2")
                time.sleep(2)
            except:
                print(" No hay más páginas, cambiando de URL")
                break

# Fin de loop URLs
print("\nProductos extraídos:")
for row in rows:
    print(row)

driver.quit()
