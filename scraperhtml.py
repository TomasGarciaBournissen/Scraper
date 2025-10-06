import asyncio
import time
from playwright.async_api import async_playwright

lock = asyncio.Lock()
MAX_WORKERS = 4
semaphore = asyncio.Semaphore(MAX_WORKERS)

# ==== Base scraper class simplificado solo para HTML ====
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
            html_content = await new_page.content()
            async with lock:
                html_list.append(html_content)
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
        await self.page.goto(self.config['url'])
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

            # scroll down halfway
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2.7)")
            await self.page.wait_for_timeout(1000)

            links = await self.obtener_links_desde_botones()
            print(f"🔎 {len(links)} productos encontrados en página {pagina}")
            for link in links:
                await self.procesar_producto(link, html_list)


# ==== Scraper de ejemplo ====
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


# ==== Función para scrapear categoría ====
async def scrape_single_category(product, html_list):
    async with semaphore:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            scraper = JumboScraper(page)
            try:
                await scraper.scrapear_url(product, html_list)
            finally:
                await browser.close()


# ==== Ejecutar scraping ====
products = ["DOWNY"]
downloaded_htmls = []

async def main(products):
    await asyncio.gather(*(scrape_single_category(prod, downloaded_htmls) for prod in products))

start = time.time()
asyncio.run(main(products))
end = time.time()

print(f"\n✅ Scraping completado en {end - start:.2f} segundos.")
print(f"Total de HTMLs descargados: {len(downloaded_htmls)}")
