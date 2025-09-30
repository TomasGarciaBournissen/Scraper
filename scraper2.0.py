import asyncio
import csv
import time
import re
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright
from playwright.async_api import Error

lock = asyncio.Lock()

# ==== Base scraper class ====
class BaseScraper:
    def __init__(self, page, config, location):
        self.page = page
        self.config = config
        self.location = location


  
    
   


    async def element_exists(self,page, xpaths, timeout=10000):
        if not xpaths:  # handles '' or None
            return False, None

        if isinstance(xpaths, str):
            xpaths = [xpaths]

        for xp in xpaths:
            if not xp.strip():  # skip empty entries in a list
                continue
            try:
                await page.wait_for_selector(f"xpath={xp}", timeout=timeout)
                return True, xp
            except:
                continue

        return False, None




    async def obtener_links_desde_botones(self):
        botones = await self.page.query_selector_all(f"xpath={self.config['xpaths']['link_button']}")
        links = []
        for btn in botones:
            try:
                href = await btn.evaluate("el => el.closest('a')?.href")
                if href and href not in links:
                    links.append(href)
            except:
                continue
        return links

    async def procesar_producto(self, link, writer):
        context = self.page.context
        new_page = await context.new_page()
        try:
            await new_page.goto(link)
            # wait for essential elements
            await new_page.wait_for_selector(f"xpath={self.config['xpaths']['brand']}", timeout=5000)

            found, discount_xpath = await self.element_exists(new_page, self.config['xpaths']['discount'], timeout=10000)
            if found:
                print("Descuento encontrado con XPath:", discount_xpath)
                sale = await new_page.text_content(f"xpath={discount_xpath}") or "N/A"
                pwd = await new_page.text_content(f"xpath={self.config['xpaths'].get('pwd','')}") or "N/A"
                price_text = await new_page.text_content(f"xpath={self.config['xpaths']['price_special']}") or "N/A"   
            else:
                print("No se encontró descuento.")
                sale = "N/A"
                pwd = "N/A"
                price_text = await new_page.text_content(f"xpath={self.config['xpaths']['price_normal']}") or "N/A"
                

            brand_text = await new_page.text_content(f"xpath={self.config['xpaths']['brand']}") or "N/A"
            name_text = await new_page.text_content(f"xpath={self.config['xpaths']['name']}") or "N/A"
            sku_text = await new_page.text_content(f"xpath={self.config['xpaths'].get('sku','')}") or "N/A"

            async with lock:
                writer.writerow({
                    "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "location": self.location,
                    "brand": self.process_brand(brand_text),
                    "name": name_text.strip(),
                    "SKU": self.process_sku(sku_text),
                    "price": self.process_price(price_text),
                    "discount": sale.strip(),
                    "PWD": pwd.strip(),
                })
            print(f"✔ Producto procesado: {name_text}")
        except Exception as e:
            print(f"❌ Error con producto {link}: {e}")
        finally:
            await new_page.close()

    async def obtener_total_paginas(self):
        pagination_xpath = self.config['xpaths'].get('pagination')
        if not pagination_xpath:
            return 1
        try:
            botones = await self.page.query_selector_all(f"xpath={pagination_xpath}")
            nums = []
            for b in botones:
                text = await b.text_content()
                if text and text.strip().isdigit():
                    nums.append(int(text.strip()))
            return max(nums) if nums else 1
        except Exception as e:
            print("Error obteniendo total de páginas:", e)
            return 1

    async def scrapear_url(self, product, writer):
        await self.page.goto(self.config['url'])
        await self.page.fill(f"xpath={self.config['xpaths']['search_box']}", product)
        await self.page.press(f"xpath={self.config['xpaths']['search_box']}", "Enter")
        await self.page.wait_for_timeout(2000)

        total_paginas = await self.obtener_total_paginas()
        print(f"Total de páginas: {total_paginas} para la URL")

        for pagina in range(1, total_paginas + 1):
            if pagina > 1:
                btn_xpath = self.config['xpaths']['pagination_btn'].format(page=pagina)
                element = await self.page.wait_for_selector(f"xpath={btn_xpath}")
                await element.scroll_into_view_if_needed()
                await element.click()
                await self.page.wait_for_timeout(2000)

            # scroll down halfway
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2.7)")
            await self.page.wait_for_timeout(1000)

            links = await self.obtener_links_desde_botones()
            print(f"🔎 {len(links)} productos encontrados en esta página")
            for link in links:
                await self.procesar_producto(link, writer)

    # Placeholder functions to be overridden if needed
    def process_brand(self, text): return text.strip() if text else "N/A"
    def process_sku(self, text): return text.strip() if text else "N/A"
    def process_price(self, text): return text.strip() if text else "N/A"

# ==== Scraper classes ====
class JumboScraper(BaseScraper):
    def __init__(self, page):
        config = {
            'url': "https://www.jumbo.com.ar/almacen/snacks",
            'xpaths': {
                'search_box': "//input[@placeholder='Buscar...']",
                'link_button': "//button[.//span[text()='Ver Producto']]",
                'brand': "//span[contains(@class,'vtex-store-components-3-x-productBrandName')]",
                'name': "//span[contains(@class,'vtex-store-components-3-x-productBrand')]",
                'sku': "//span[contains(@class,'vtex-product-identifier-0-x-product-identifier__value')]",
                'price_special': "//div[@class='jumboargentinaio-store-theme-2t-mVsKNpKjmCAEM_AMCQH']",
                'price_normal': "//div[contains(@class,'vtex-price-format-gallery')]",
                'discount': ["//span[contains(@class, 'jumboargentinaio-store-theme-MnHW0PCgcT3ih2-RUT-t_')]","//span[contains(@class, 'jumboargentinaio-store-theme-Aq2AAEuiQuapu8IqwN0Aj')]"],
                'pwd': "//div[contains(@class,'vtex-price-format-gallery')]",
                'pagination': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]",
                'pagination_btn': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='{page}']"
            }
        }
        super().__init__(page, config, "Jumbo")

class CotoScraper(BaseScraper):
    def __init__(self, page):
        config = {
            'url': "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio",
            'xpaths': {
                'search_box': "//input[@placeholder='¿Qué querés comprar hoy?']",
                'link_button': "//div[contains(@class, 'producto-card')]",
                'brand': "//td[span[normalize-space()='MARCA']]",
                'name': "//h2[contains(@class, 'title') and contains(@class, 'text-dark')]",
                'sku': "//span[i[contains(@class, 'fa-shopping-basket')]]",
                'price_special': "//div[@class='mt-2 small ng-star-inserted' and b[text()='Precio regular :']]",
                'price_normal': "//var[contains(@class,'price')]",
                'discount': "//div[@class='mb-2 ng-star-inserted']",
                'pwd': "//var[contains(@class,'price')]", 
                'pagination': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]",
                'pagination_btn': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]//a[normalize-space(text())='{page}']"
            }
        }
        super().__init__(page, config, "Coto")

    async def obtener_links_desde_botones(self):
        base_url = "https://www.cotodigital.com.ar"
        botones = await self.page.query_selector_all(f"xpath={self.config['xpaths']['link_button']}")
        links = []

        for btn in botones:
            try:          
                href_element = await btn.query_selector("xpath=.//a[contains(@href, '/sitios/cdigi/productos/')]")
                if href_element:
                    href = await href_element.get_attribute("href")
                    if href:
                        # Prepend base_url if the link is relative
                        if href.startswith("/"):
                            href = base_url + href
                        if href not in links:
                            links.append(href)
            except Exception as e:
                print("Error obteniendo link:", e)
                continue

        return links


    def process_brand(self, text):
        match = re.search(r'(?i)marca:\s*(.+)', text)
        return match.group(1).strip() if match else "N/A"

    def process_sku(self, text):
        match = re.search(r'\b(?:sku|ean)\s*:\s*(.+)', text, re.IGNORECASE)
        return match.group(1).strip() if match else "N/A"

    def process_price(self, text):
        match = re.search(r'[\$€]?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})', text)
        return match.group(0).strip() if match else "N/A"

# ==== Function to scrape single category ====
async def scrape_single_category(product):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        context = await browser.new_context()
        page = await context.new_page()

        scrapers = [CotoScraper(page), JumboScraper(page)]
        try:
            for scraper in scrapers:
                with open("precios_playwright.csv", mode="a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=["date","location","brand","name","SKU","price","discount","PWD"])
                    await scraper.scrapear_url(product, writer)
        finally:
            await browser.close()

# ==== Parallel execution ====
products = ["alfajor oreo",]

async def main():
    # This gathers the coroutines correctly
    await asyncio.gather(*(scrape_single_category(prod) for prod in products))

if __name__ == "__main__":
    start = time.time()

    # Prepare CSV file
    with open("precios_playwright.csv", mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date","location","brand","name","SKU","price","discount","PWD"])
        writer.writeheader()

    # Run async main coroutine
    asyncio.run(main())

    end = time.time()
    print(f"\n✅ Scraping completado en {end - start:.2f} segundos.")
