from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
import time

def open_page(url):
    chrome_options = Options()
    # Add any options if needed, e.g., headless:
    # chrome_options.add_argument("--headless")

    driver = webdriver.Remote(
        command_executor='http://localhost:4444/wd/hub',
        options=chrome_options
    )
    
    print(f"Page opened")
    driver.get(url)
    time.sleep(10)  # Keep browser open 10 seconds so you can see it
    driver.quit()
    print(f"Page closed")


urls = [
    "https://www.jumbo.com.ar/dove?_q=dove&map=ft",
    "https://www.jumbo.com.ar/pantene?_q=pantene&map=ft",
    "https://www.jumbo.com.ar/downy?_q=downy&map=ft",
    "https://www.jumbo.com.ar/elvive?_q=elvive&map=ft",
    "https://www.jumbo.com.ar/comfort%20suavizante?_q=comfort%20suavizante&map=ft",
    "https://www.jumbo.com.ar/gillete?_q=gillete&map=ft",
]


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=2) as executor:
        for ulr in urls:
            executor.submit(open_page, ulr)