from playwright.sync_api import sync_playwright
import time
import re
import json
import sys
import os
import threading
import http.server
import requests


def parse_schedule(schedule_text):
    match = re.search(r'(\d+)\s*(min|h)', schedule_text.lower())
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        return value * 60 if unit == 'h' else value
    return float('inf')


def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def get_bus_details(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector('body')
        time.sleep(3)

        bus_elements = page.query_selector_all('app-departure-from-now')
        bus_info = []

        for bus in bus_elements:
            try:
                # Extract direction and clean up text
                name_element = bus.query_selector('.direction')
                name = (
                    name_element.inner_text()
                    .replace('vers ', '')
                    .strip()
                    .replace('\n', ' ')
                    if name_element
                    else None
                )

                if not name or name.lower() == 'vers':
                    continue

                # Extract schedule and clean up text
                schedule_element = bus.query_selector('.schedule')
                if schedule_element:
                    schedule_text = schedule_element.inner_text().replace('\n', ' ')

                    if 'proche' in schedule_text.lower():
                        schedule = 'proche'
                        sort_value = 0
                    else:
                        match = re.search(r'(\d+)\s*(min|h)', schedule_text.lower())
                        schedule = match.group(0) if match else 'N/A'
                        sort_value = parse_schedule(schedule_text)

                # Extract image source
                image_element = bus.query_selector('img.picto-line')
                image_url = image_element.get_attribute('src') if image_element else None
                if image_url:
                    image_filename = f"{sanitize_filename(name)}.png"
                    image_path = os.path.join(os.path.dirname(__file__), image_filename)
                    response = requests.get(image_url)
                    if response.status_code == 200:
                        with open(image_path, 'wb') as img_file:
                            img_file.write(response.content)

                bus_entry = {
                    'direction': name,
                    'schedule': schedule,
                    'image': image_filename if image_url else None,
                    'sort_value': sort_value,
                }

                # Extract disruption and clean up text
                disruption_element = bus.query_selector('.disruptions.ng-star-inserted')
                if disruption_element:
                    disruption = disruption_element.inner_text().strip().replace('\n', ' ')
                    disruption = disruption.split('\n')[0] if '\n' in disruption else disruption
                    if disruption and disruption.lower() != 'no disruption':
                        # Remove 'Plus d\'infos +' from disruption text
                        disruption = disruption.replace('Plus d\'infos +', '').strip()
                        if disruption:
                            bus_entry['disruption'] = disruption

                bus_info.append(bus_entry)
            except Exception as e:
                print(f"Error extracting bus info: {e}")

        browser.close()

        return [
            {k: v for k, v in bus.items() if k != 'sort_value'}  # Omit 'sort_value'
            for bus in sorted(bus_info, key=lambda x: x['sort_value'])
        ]


def start_server():
    """Start a simple HTTP server to serve the current directory"""
    os.chdir(os.path.dirname(__file__))  # Ensure the server runs from the script's directory
    handler = http.server.SimpleHTTPRequestHandler
    with http.server.HTTPServer(('localhost', 8000), handler) as httpd:
        print("Server started at http://localhost:8000")
        httpd.serve_forever()


def main():
    # Start the server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()

    # Allow URL to be passed as a command-line argument
    url = sys.argv[1] if len(sys.argv) > 1 else "https://aix.ami.mobireport.fr/fr/stop/40865"
    output_file = os.path.join(os.path.dirname(__file__), "bus.json")

    while True:
        try:
            result = get_bus_details(url)
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Bus schedule updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(10)
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()
