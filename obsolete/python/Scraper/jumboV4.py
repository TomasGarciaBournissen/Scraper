from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Remote
from concurrent.futures import ThreadPoolExecutor
import csv,time,os,re,threading
import signal
import sys

interrupted = threading.Event()

def handle_sigint(signum, frame):
    print("\n[!] Interrupción detectada. Cerrando procesos...")
    interrupted.set()
    sys.exit(0)

signal.signal(signal.SIGINT, handle_sigint)
# Setup ChromeService
Grid_URL = "http://localhost:4444/wd/hub"
def get_chrome_options():
    options = Options()
    #options.add_argument("--headless")
    #options.add_argument("--disable-gpu")
    #prefs = {"profile.managed_default_content_settings.images": 2}
    #options.add_experimental_option("prefs", prefs)
    #options.set_capability("pageLoadStrategy", "eager")
    options.add_argument("--start-maximized")
    return options






def filter_weight(name):
    match = re.search( r'(?i)\b(?:x\s*)?(\d+(?:\.\d+)?)\s*(ml|g|gr|l|kg|un|cc)(?:\s*x)?\b', name)
    if match:
        number = match.group(1)
        unit = match.group(2).lower()
        return f"{number} {unit}"
    return "N/A"

#definir si el elemento existe o no 
def element_exists(driver,xpath):
    try:

        WebDriverWait(driver, 4).until(EC.presence_of_element_located((By.XPATH, xpath)))
        return True
    except TimeoutException:
        return False



#filtra el precio por litro o gramo de un producto
def filter_price(text):
    pattern = r"(x\s*\d*\s*(?:lt|ml|g|kg|un|cc)\.?:\s*\$[\d\.,]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ""
    
    raw = match.group(1)
    # Normalize spacing after x
    normalized = re.sub(r"^x\s*", "x ", raw, flags=re.IGNORECASE)
    # Remove spaces between number and unit for consistency
    normalized = re.sub(r"(\d)\s+(?=(?:lt|ml|g|kg|un|cc))", r"\1", normalized, flags=re.IGNORECASE)
    # Ensure single space before colon
    normalized = re.sub(r"\s*:\s*", ": ", normalized)
    return normalized.strip()

#obtiene los links de los productos desde el boton de cada producto
def obtener_links_desde_botones(driver):
    product_buttons = WebDriverWait(driver, 10).until(
        EC.presence_of_all_elements_located((By.XPATH, "//button[.//span[text()='Ver Producto']]"))
    )
    links = []
    for btn in product_buttons:
        try:
            href = btn.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
            if href and href not in links:
                links.append(href)
        except:
            continue
    return links


#procesa cada producto, abre el link, saca los datos y los guarda en el csv 
def procesar_producto(driver,link, writer,lock):
    try:
        orig = driver.current_window_handle
        driver.execute_script("window.open(arguments[0]);", link)
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) == 2)
        new = [w for w in driver.window_handles if w != orig][0]
        driver.switch_to.window(new)

        
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class,'vtex-store-components-3-x-productBrandName')]"))
        )

        # Check if discount span is present and visible
        discount_xpath = "//span[contains(@class, 'jumboargentinaio-store-theme-3Hc7_vKK9au6dX_Su4b0Ae')]"
        if element_exists(driver, discount_xpath):
            sale = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, discount_xpath))
            ).text
            pwd = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'vtex-price-format-gallery')]"))
            ).text
            price = WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.XPATH, "//div[@class='jumboargentinaio-store-theme-2t-mVsKNpKjmCAEM_AMCQH']"))
            ).text
        else:
            price = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//div[contains(@class,'vtex-price-format-gallery')]"))
            ).text
            sale = "N/A"
            pwd = "N/A"

        # Wait and collect the rest of the required fields
        brand = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(@class,'vtex-store-components-3-x-productBrandName')]"))
        ).text

        name = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(@class,'vtex-store-components-3-x-productBrand')]"))
        ).text

        weight = filter_weight(name)

        pbw_text = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(@class,'vtex-custom-unit-price')]"))
        ).text
        print(f"PBW text: {pbw_text}")

        sku = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//span[contains(@class,'vtex-product-identifier-0-x-product-identifier__value')]"))
        ).text

        pbw = filter_price(pbw_text)
        with lock:
            writer.writerow({"brand": brand, "name": name, "SKU": sku, "price": price, "weight": weight, "PBW": pbw, "discount": sale, "PWD": pwd,})

        print(f" Producto procesado:")

        driver.close()
        driver.switch_to.window(orig)

    except Exception as e:
        print(f" Error con producto {link}: {e}")
        try:
            driver.close()
            driver.switch_to.window(orig)
        except:
            pass



# determina si hay mas de una pagina de resultados para la busqueda especifica y devuelve el total de paginas
def obtener_total_paginas(driver):
    try:
        botones = driver.find_elements(By.XPATH, "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]")
        nums = [int(b.text.strip()) for b in botones if b.text.strip().isdigit()]
        return max(nums) if nums else 1
    except:
        return 1


# scrapea una url especifica usando todas las funciones anteriores y el driver de selenium para navegar de manera automatizada
def scrapear_url(driver,url, writer, lock):
    driver.get(url)
    time.sleep(2)

    total_paginas = obtener_total_paginas(driver)
    print(f" Total de páginas: {total_paginas} para la URL {url}")

    for pagina in range(1, total_paginas + 1):
        print(f"\n Página {pagina}/{total_paginas}")
        if pagina > 1:
            btn_xpath = f"//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='{pagina}']"
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, btn_xpath))).click()
            time.sleep(2)

        total_h = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script(f"window.scrollTo(0, {total_h/2.7});")
        time.sleep(1)

        links = obtener_links_desde_botones(driver)
        print(f" {len(links)} productos encontrados en esta página")
        for link in links:
            if interrupted.is_set():
                print("[!] Cancelando procesamiento por interrupción.")
                return
            procesar_producto(driver,link, writer, lock)


def scrape_single_url(url, lock):
    options = get_chrome_options()
    driver = Remote(command_executor=Grid_URL, options=options)
    try:
        with open("preciosV2.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["brand", "name", "price", "PBW", "SKU", "discount", "PWD", "weight"])
                
            scrapear_url(driver,url, writer, lock)
    finally:
        driver.quit()







# URLs a scrapear
urls = [
    "https://www.jumbo.com.ar/colgate?_q=colgate&map=ft",
    "https://www.jumbo.com.ar/sedal?_q=sedal&map=ft",
    "https://www.jumbo.com.ar/johnson%20%26%20johnson?%20JOHNSON&_q=JOHNSON%20&map=ft",
    "https://www.jumbo.com.ar/dove?_q=dove&map=ft",
    "https://www.jumbo.com.ar/pantene?_q=pantene&map=ft",
    "https://www.jumbo.com.ar/downy?_q=downy&map=ft",
    "https://www.jumbo.com.ar/elvive?_q=elvive&map=ft",
    "https://www.jumbo.com.ar/comfort%20suavizante?_q=comfort%20suavizante&map=ft",
    "https://www.jumbo.com.ar/gillete?_q=gillete&map=ft",
    "https://www.jumbo.com.ar/vivere%20suavizante?_q=vivere%20suavizante&map=ft",
    "https://www.jumbo.com.ar/bic%20cuidado%20personal?_q=BIC%20cuidado%20personal&map=ft",
    "https://www.jumbo.com.ar/venus?_q=VENUS&map=ft",
    "https://www.jumbo.com.ar/ayudin?_q=ayudin&map=ft",


]

start = time.time()

lock = threading.Lock()

with ThreadPoolExecutor(max_workers=12) as executor:
    with open("preciosV2.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["brand", "name", "price", "PBW", "SKU", "discount", "PWD", "weight"])
            file_exists = os.path.isfile("preciosV2.csv") and os.stat("preciosV2.csv").st_size > 0
            if not file_exists:
                writer.writeheader()


    futures = [executor.submit(scrape_single_url, url, lock) for url in urls]

    for future in futures:
        try:
            future.result()
        except Exception as e:
            print(f"Error al procesar una URL: {e}")


end = time.time()
print(f"\n Scraping completado en {end - start:.2f} segundos.")