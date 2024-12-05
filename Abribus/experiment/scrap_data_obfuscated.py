from playwright.sync_api import sync_playwright
import time

def get_bus_info(url):
    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch()
        page = browser.new_page()
        
        # Navigate to page
        page.goto(url)
        
        # Wait for potential dynamic content to load
        page.wait_for_selector('body')
        time.sleep(3)  # Additional wait for JavaScript rendering
        
        # Extract text content or use page.locator() to find specific elements
        page_text = page.content()
        
        browser.close()
        return page_text

# Replace with your actual URL
url = "https://aix.ami.mobireport.fr/fr/stop/40865"
result = get_bus_info(url)
print(result)