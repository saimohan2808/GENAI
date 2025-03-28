import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import google.generativeai as genai
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variables
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)
else:
    raise ValueError("GEMINI_API_KEY is missing in the environment variables.")

RELEVANT_KEYWORDS = ["mission", "values", "about", "history", "leadership", "team", "executives", "awards", "products", "services"]

def get_relevant_links(base_url):
    """Retrieve relevant internal links based on predefined keywords."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"}
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        base_domain = urlparse(base_url).netloc
        links = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(base_url, href)
            if urlparse(full_url).netloc == base_domain and any(keyword in full_url.lower() for keyword in RELEVANT_KEYWORDS):
                links.add(full_url)
        
        return list(links)
    except Exception as e:
        print(f"Error fetching links from {base_url}: {e}")
        return []

def scrape_website(url):
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=5, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retry))
    
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        main_content = soup.find('main') or soup.find('body')
        text = main_content.get_text(separator=' ', strip=True) if main_content else ""
        return text
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return ""

def extract_info(text):
    """Uses LLM (Gemini) to extract structured information."""
    prompt = f"""
    Extract the following company details from the given text. If a detail is not found, explicitly state "Not Available".
    Mission statement or core values
    Products or services offered
    Founding year and founders
    Headquarters location
    Key executives or leadership team
    Notable awards or recognitions
    
    Text:
    {text}
    """
    
    model_name = "gemini-1.5-flash"
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        extracted_text = response.text.replace("**", "") if hasattr(response, 'text') else "Extraction failed"
        return extracted_text
    except Exception as e:
        print(f"Error extracting info: {e}")
        return "Extraction failed"

def main(urls):
    data = []
    for base_url in urls:
        print(f"Processing base URL: {base_url}")
        relevant_urls = get_relevant_links(base_url)
        relevant_urls.append(base_url)
        combined_text = ""
        
        for url in relevant_urls:
            print(f"Scraping: {url}")
            text = scrape_website(url)
            if text:
                combined_text += text + "\n"
            time.sleep(2)
        
        extracted_data = extract_info(combined_text) if combined_text else "Scraping failed"
        data.append([base_url, extracted_data])
    
    df = pd.DataFrame(data, columns=["Website", "Extracted Information"])
    df.to_csv("company_details.csv", index=False)
    print("Data saved to company_details.csv")

urls = [
    "https://www.snap.com",
    "https://www.dropbox.com",
    "https://www.tesla.com",
    "https://www.spacex.com",
    "https://robinhood.com",
    "https://stripe.com",
    "https://squareup.com",
    "https://www.shopify.com",
    "https://www.zara.com",
    "https://hmgroup.com"
]
main(urls)