import asyncio
import time
import os
from datetime import datetime
from playwright.async_api import async_playwright

lock = asyncio.Lock()
MAX_WORKERS = 4
semaphore = asyncio.Semaphore(MAX_WORKERS)

class BaseScraper:
    def __init__(self, page, config, location):
        self.page = page
        self.config = config
        self.location = location

    async def element_exists(self, page, xpaths, timeout=4000):
        if not xpaths:
            return False, None
        if isinstance(xpaths, str):
            xpaths = [xpaths]
        for xp in xpaths:
            if not xp.strip():
                continue
            try:
                await page.wait_for_selector(f"xpath={xp}", timeout=timeout)
                return True, xp
            except:
                continue
        return False, None

    async def obtener_links_desde_botones(self):
        try:
            await self.page.wait_for_selector(f"xpath={self.config['xpaths']['link_button']}", timeout=10000)
        except:
            print("⚠ No se encontraron botones de producto en el timeout")
            return []

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

    async def procesar_producto(self, link, html_list):
        context = self.page.context
        new_page = await context.new_page()
        try:
            await asyncio.wait_for(self._procesar_producto_inner(new_page, link, html_list), timeout=20)
        except asyncio.TimeoutError:
            print(f"⏱ Timeout procesando producto {link}")
        except Exception as e:
            print(f"❌ Error con producto {link}: {e}")
        finally:
            await new_page.close()

    async def _procesar_producto_inner(self, new_page, link, html_list):
        try:
            await new_page.goto(link, timeout=8000, wait_until="domcontentloaded")
            await self.page.wait_for_timeout(10000)
            html_content = await new_page.content()
            async with lock:
                html_list.append((link, html_content))
            print(f"✔ HTML descargado: {link}")
        except Exception as e:
            print(f"⚠️ Error cargando {link}: {e}")

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

    async def scrapear_url(self, product, html_list):
        await self.page.goto(self.config['url'], wait_until="domcontentloaded", timeout=60000)
        await self.page.wait_for_selector(f"xpath={self.config['xpaths']['search_box']}", state="visible", timeout=30000)
        await self.page.wait_for_timeout(10000)
        await self.page.fill(f"xpath={self.config['xpaths']['search_box']}", product)
        await self.page.press(f"xpath={self.config['xpaths']['search_box']}", "Enter")
        await self.page.wait_for_timeout(2000)
        


        total_paginas = await self.obtener_total_paginas()
        print(f"Total de páginas: {total_paginas} para {product}")

        for pagina in range(1, total_paginas + 1):
            if pagina > 1:
                viewport = self.page.viewport_size
                if viewport:
                    x, y = 5, viewport['height'] // 2
                    await self.page.mouse.click(x, y)
                    await self.page.wait_for_timeout(200)
                btn_xpath = self.config['xpaths']['pagination_btn'].format(page=pagina)
                element = await self.page.wait_for_selector(f"xpath={btn_xpath}", timeout=5000)
                await element.scroll_into_view_if_needed()
                await element.click()
                await self.page.wait_for_timeout(2000)

            
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2.7)")
            await self.page.wait_for_timeout(1000)

            links = await self.obtener_links_desde_botones()
            print(f"🔎 {len(links)} productos encontrados en página {pagina}")
            for link in links:
                await self.procesar_producto(link, html_list)



class JumboScraper(BaseScraper):
    def __init__(self, page):
        config = {
            'url': "https://www.jumbo.com.ar/almacen/snacks",
            'xpaths': {
                'search_box': "//input[@placeholder='Buscar...']",
                'link_button': "//button[.//span[text()='Ver Producto']]",
                'pagination': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]",
                'pagination_btn': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='{page}']"
            }
        }
        super().__init__(page, config, "Jumbo")

class DiscoScraper(BaseScraper):
    def __init__(self, page):
        config = {
            'url': "https://www.disco.com.ar/?gclsrc=aw.ds&gad_source=1&gad_campaignid=11002659319&gbraid=0AAAAADR-xG-NXLsgewPYAeKaSnO4cqe_Z&gclid=CjwKCAjw0sfHBhB6EiwAQtv5qTjzE-TfUU9R_JhzTwTktU5TAo1YwFMkf8Sc5ovPuPvJWl5mAvEaihoCBhoQAvD_BwE",
            'xpaths': {
                'search_box': "//input[@placeholder='Buscar...']",
                'link_button': "//button[.//span[text()='Ver Producto']]",
                'pagination': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before')]",
                'pagination_btn': "//button[contains(@class,'discoargentina-search-result-custom-1-x-option-before') and normalize-space(text())='{page}']"
            }
        }
        super().__init__(page, config, "Disco")

class CotoScraper(BaseScraper):
    def __init__(self, page):
        config = {
            'url': "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio",
            'xpaths': {
                'search_box': "//input[@placeholder='¿Qué querés comprar hoy?']",
                'link_button': "//div[contains(@class, 'producto-card')]", 
                'pagination': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]",
                'pagination_btn': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]//a[normalize-space(text())='{page}']"
            }
        }
        super().__init__(page, config, "Coto")

class CotoScraper(BaseScraper):
    def __init__(self, page):
        config = {
            'url': "https://www.cotodigital.com.ar/sitios/cdigi/nuevositio",
            'xpaths': {
                'search_box': "//input[@placeholder='¿Qué querés comprar hoy?']",
                'link_button': "//div[contains(@class, 'producto-card')]", 
                'pagination': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]",
                'pagination_btn': "//li[contains(@class, 'page-item') and contains(@class, 'ng-star-inserted')]//a[normalize-space(text())='{page}']"
            }
        }
        super().__init__(page, config, "Coto")

    async def obtener_links_desde_botones(self):
        base_url = "https://www.cotodigital.com.ar"
        botones = await self.page.query_selector_all(f"xpath={self.config['xpaths']['link_button']}")
        links = []
        print(f"Botones encontrados: {len(botones)}")
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

async def scrape_single_category(scraper_class, product, html_list):
    async with semaphore:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            scraper = scraper_class(page)
            try:
                await scraper.scrapear_url(product, html_list)
            finally:
                await browser.close()




scrapers = [JumboScraper]#JumboScraper, CotoScraper
products = ["DOWNY",]

downloaded_htmls = []

async def main():
    tasks = [
        scrape_single_category(scraper, product, downloaded_htmls)
        for scraper in scrapers
        for product in products
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Log any scraper exceptions for debugging
    for res in results:
        if isinstance(res, Exception):
            print(f"⚠️ Task error: {res}")


asyncio.run(main())

output_dir = "downloaded_htmls"
os.makedirs(output_dir, exist_ok=True)

print(f"📄 Total HTMLs descargados: {len(downloaded_htmls)}")
for link, _ in downloaded_htmls:
    print("➡", link)


for i, (link, html) in enumerate(downloaded_htmls, start=1):
    site = "jumbo" if "jumbo.com.ar" in link else "coto"
    site_dir = os.path.join(output_dir, site)
    os.makedirs(site_dir, exist_ok=True)
    safe_name = f"page_{i}.html"
    output_path = os.path.join(site_dir, safe_name)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- {link} -->\n")
        f.write(html)
    print(f"💾 Guardado: {output_path}")


print(f"Total de HTMLs descargados: {len(downloaded_htmls)}")
print(f"📂 Archivos guardados en carpeta: {output_dir}")
