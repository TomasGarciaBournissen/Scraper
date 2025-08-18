from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Remote
from concurrent.futures import ThreadPoolExecutor
import csv, time, os, re, threading, signal, sys

# ==== manejo de interrupción ====
interrupted = threading.Event()




# ==== opciones de Chrome y Grid ====
Grid_URL = "http://localhost:4444/wd/hub"
def get_chrome_options():
    options = Options()
    #options.add_argument("--headless")
    #options.add_argument("--disable-gpu")
    options.add_argument("--start-maximized")
    return options

lock = threading.Lock()

# ==== Clase base con toda la lógica original ====
class BaseScraper:
    
    
    
    def __init__(self, driver, config, location):
        self.driver = driver
        self.config = config
        self.location = location

    def process_sku(self, sku_text):
        return sku_text 

    

    def element_exists(self, xpath, timeout=4):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            return True
        except TimeoutException:
            return False

    def process_brand(self, brand_text):
        return brand_text

    def filter_weight(self, name):
        match = re.search(r'(?i)\b(?:x\s*)?(\d+(?:\.\d+)?)\s*(ml|g|gr|l|kg|un|cc)\b', name)
        return f"{match.group(1)} {match.group(2)}" if match else "N/A"

    def filter_price(self, text):
        pattern = r"(x\s*\d*\s*(?:lt|ml|g|kg|un|cc)\.?:\s*\$[\d\.,]+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            return ""
        raw = match.group(1)
        normalized = re.sub(r"^x\s*", "x ", raw, flags=re.IGNORECASE)
        normalized = re.sub(r"(\d)\s+(?=(?:lt|ml|g|kg|un|cc))", r"\1", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*:\s*", ": ", normalized)
        return normalized.strip()

    def obtener_links_desde_botones(self):
        botones = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, self.config['xpaths']['link_button']))
        )
        links = []
        for btn in botones:
            try:
                href = btn.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
                if href and href not in links:
                    links.append(href)
            except:
                continue
        return links

    def process_price(self, price_text):
        return  price_text

    def procesar_producto(self, link, writer):
        try:
            orig = self.driver.current_window_handle
            self.driver.execute_script("window.open(arguments[0]);", link)
            WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) == 2)
            new = [w for w in self.driver.window_handles if w != orig][0]
            self.driver.switch_to.window(new)

            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, self.config['xpaths']['brand']))
            )

            if self.element_exists(self.config['xpaths']['discount']):
                sale = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['discount']))
                ).text
                pwd = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['pwd']))
                ).text
                price_text = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['price_special']))
                ).text
                price = self.process_price(price_text)
            else:
                price = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['price_normal']))
                ).text
                sale = "N/A"
                pwd = "N/A"

            brand_text = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['brand']))
            ).text

            brand = self.process_brand(brand_text)

            name = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['name']))
            ).text

            weight = self.filter_weight(name)
            pbw_text = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['pbw']))
            ).text

            sku_text = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, self.config['xpaths']['sku']))
            ).text

            sku = self.process_sku(sku_text)

            pbw = self.filter_price(pbw_text)

            with lock:
                writer.writerow({
                    "location": self.location,
                    "brand": brand,
                    "name": name,
                    "SKU": sku,
                    "price": price,
                    "weight": weight,
                    "PBW": pbw,
                    "discount": sale,
                    "PWD": pwd,
                })

            print(f" Producto procesado: {name}")
            self.driver.close()
            self.driver.switch_to.window(orig)

        except Exception as e:
            print(f" Error con producto {link}: {e}")
            try:
                self.driver.close()
                self.driver.switch_to.window(orig)
            except:
                pass

    def obtener_total_paginas(self):
        try:
            botones = self.driver.find_elements(By.XPATH, self.config['xpaths']['pagination'])
            nums = [int(b.text.strip()) for b in botones if b.text.strip().isdigit()]
            return max(nums) if nums else 1
        except:
            return 1

    def scrapear_url(self, url, writer):
        self.driver.get(url)
        time.sleep(2)
        total_paginas = self.obtener_total_paginas()
        print(f" Total de páginas: {total_paginas} para la URL {url}")

        for pagina in range(1, total_paginas + 1):
            print(f"\n Página {pagina}/{total_paginas}")
            if pagina > 1:
                
                btn_xpath = self.config['xpaths']['pagination_btn'].format(page=pagina)
                
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, btn_xpath))
                )
                print(f" Elemento encontrado:")
                
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5) 
                
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, btn_xpath))
                ).click()
                
                time.sleep(2)

            total_h = self.driver.execute_script("return document.body.scrollHeight")
            self.driver.execute_script(f"window.scrollTo(0, {total_h/2.7});")
            time.sleep(1)

            links = self.obtener_links_desde_botones()
            print(f" {len(links)} productos encontrados en esta página")
            for link in links:
                if interrupted.is_set():
                    print("[!] Cancelando procesamiento por interrupción.")
                    return
                self.procesar_producto(link, writer)

# ==== Clase específica Jumbo ====
class JumboScraper(BaseScraper):
    def __init__(self, driver):


        config = {
            'xpaths': {
                'link_button': "//button[.//span[text()='Ver Producto']]",
                'brand': "//span[contains(@class,'vtex-store-components-3-x-productBrandName')]",
                'name': "//span[contains(@class,'vtex-store-components-3-x-productBrand')]",
                'sku': "//span[contains(@class,'vtex-product-identifier-0-x-product-identifier__value')]",
                'price_special': "//div[@class='jumboargentinaio-store-theme-2t-mVsKNpKjmCAEM_AMCQH']",
                'price_normal': "//div[contains(@class,'vtex-price-format-gallery')]",
                'discount': "//span[contains(@class, 'jumboargentinaio-store-theme-3Hc7_vKK9au6dX_Su4b0Ae')]",
                'pwd': "//div[contains(@class,'vtex-price-format-gallery')]",
                'pbw': "//span[contains(@class,'vtex-custom-unit-price')]",
                'pagination': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]",
                'pagination_btn': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='{page}']"
            }
        }
        super().__init__(driver, config, location= "Jumbo")
class CotoScraper(BaseScraper):
    def __init__(self, driver):

        

        config = {
            'xpaths' : {
                'link_button': "//div[contains(@class, 'producto-card')]",
                'brand': "//td[span[normalize-space()='MARCA']]",
                'name': "//h2[contains(@class, 'title') and contains(@class, 'text-dark')]",
                'sku': "//span[i[contains(@class, 'fa-shopping-basket')]]",
                'price_special': "//div[@class='mt-2 small ng-star-inserted' and b[text()='Precio regular :']]",
                'price_normal': "//var[contains(@class,'price')]",
                'discount': "//b[@class='text-success']",
                'pwd': "//var[contains(@class,'price')]", 
                'pbw': "//div[contains(@class,'small') and contains(@class,'ng-star-inserted') and b[contains(text(),'por')]]",
                'pagination': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]",
                'pagination_btn': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]//a[normalize-space(text())='{page}']"
            }
        }
        super().__init__(driver, config, location="Coto")

    def obtener_links_desde_botones(self):
        # Wait for all product card containers
        botones = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, self.config['xpaths']['link_button']))
        )
        links = []
        for btn in botones:
            try:
                # Find the product link <a> inside this container
                href_element = btn.find_element(By.XPATH, ".//a[contains(@href, '/sitios/cdigi/productos/')]")
                href = href_element.get_attribute("href")
                if href and href not in links:
                    links.append(href)
            except:
                continue
        return links

    def process_brand(self, brand_text):
        match = re.search(r'(?i)marca:\s*(.+)', brand_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "N/A"
    
    

    def process_sku(self, sku_text):
        match = re.search(r'\b(?:sku|ean)\s*:\s*(.+)', sku_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "N/A"
    
    def process_price(self, price_text):
        match = re.search(r'\b(?:regular)\s*:\s*(.+)', price_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return "N/A"

# ==== Función para cada hilo ====
def scrape_single_url(url):
    options = get_chrome_options()
    driver = Remote(command_executor=Grid_URL, options=options)
    try:
        scraper = CotoScraper(driver)
        


        
        with open("preciosV2.csv", mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["location", "brand", "name", "SKU", "price", "weight", "PBW", "discount", "PWD"]
            )
    
            scraper.scrapear_url(url, writer)
    finally:
        driver.quit()

# ==== Lista de URLs y ejecución paralela ====
if __name__ == "__main__":
    
    urls = [
       
      
       
        
       
        "https://www.jumbo.com.ar/downy?_q=downy&map=ft",
       
        "https://www.jumbo.com.ar/comfort%20suavizante?_q=comfort%20suavizante&map=ft",
        
        "https://www.jumbo.com.ar/vivere%20suavizante?_q=vivere%20suavizante&map=ft",
        
        ]
    
    """
    urls = [
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=downy&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=elvive&idSucursal=200", 
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=pantene&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=sedal&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=dove&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=gillete&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=comfort&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=ayudin&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=colgate&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=venus&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=bic%20afeitar&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=vivere&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria/brand-johnson-johnson/_/N-133sd2p?Dy=1&Nf=product.startDate%7CLTEQ%201.7522784E12%7C%7Cproduct.endDate%7CGTEQ%201.7522784E12&Nr=AND(product.sDisp_200:1004,product.language:español,OR(product.siteId:CotoDigital))&assemblerContentCollection=%2Fcontent%2FShared%2FAuto-Suggest%20Panels&idSucursal=200",
        "https://www.cotodigital.com.ar/sitios/cdigi/categoria?_dyncharset=utf-8&Dy=1&Ntt=elvive&idSucursal=200",
        
    
    ]
    """

    start = time.time()
    with open("preciosV2.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["location", "brand", "name", "SKU", "price", "weight", "PBW", "discount", "PWD"])
        writer.writeheader()
    with ThreadPoolExecutor(max_workers=12) as executor:
        executor.map(scrape_single_url, urls)
        time.sleep(1)

    end = time.time()
    print(f"\n Scraping completado en {end - start:.2f} segundos.")
