import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import pandas as pd
from bs4 import BeautifulSoup

job_urls = {
    'Business Analyst': 'https://www.naukri.com/business-analyst-jobs-in-delhi-ncr?k=business%20analyst&l=delhi%20%2F%20ncr%2C%20gurugram%2C%20noida&experience=4',
    'Senior Business Analyst': 'https://www.naukri.com/senior-business-analyst-jobs-in-delhi-ncr?k=senior%20business%20analyst&l=delhi%20%2F%20ncr%2C%20gurugram%2C%20noida&experience=4',
    'Data Analyst': 'https://www.naukri.com/data-analyst-jobs-in-delhi-ncr?k=data%20analyst&l=delhi%20%2F%20ncr%2C%20gurugram%2C%20noida&experience=4',
    'Product Manager': 'https://www.naukri.com/product-manager-jobs-in-delhi-ncr?k=product%20manager&l=delhi%20%2F%20ncr%2C%20gurugram%2C%20noida&experience=4'
}

async def scrape_tab(context, category, url):
    """Opens a new tab (page) within the same browser context."""
    page = await context.new_page()
    
    # Apply stealth
    stealth_config = Stealth()
    await stealth_config.apply_stealth_async(page)
    
    print(f"🚀 Scraping: {category}")
    
    try:
        # Navigate to the page
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # Wait for the page to load
        await asyncio.sleep(5)
        
        # Get the page HTML content
        html_content = await page.content()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
        
        results = []
        
        for job in job_cards:
            # Job Title
            title_tag = job.find('a', class_='title')
            # Company Name
            company_tag = job.find('a', class_='comp-name')
            # Experience for the job
            experience_tag = job.find('span', class_='exp-wrap')
            # Location of the job
            location_tag = job.find('span', class_='loc-wrap')
            
            if title_tag:
                job_dict = {
                    'Category': category,
                    'Title': title_tag.text.strip() if title_tag else 'N/A',
                    'Company': company_tag.text.strip() if company_tag else 'N/A',
                    'Experience': experience_tag.text.strip() if experience_tag else 'N/A',
                    'Location': location_tag.text.strip() if location_tag else 'N/A',
                    'Link': title_tag.get('href', 'N/A')
                }
                results.append(job_dict)
        
        print(f"✅ Found {len(results)} jobs for {category}")
        return results
        
    except Exception as e:
        print(f"⚠️ Error in {category}: {e}")
        return []
    finally:
        await page.close()

async def main():
    async with async_playwright() as p:
        # Launch with additional anti-detection flags
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        
        # Create context with more realistic settings
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='Asia/Kolkata',  # Match your location
            permissions=['geolocation'],
            geolocation={'latitude': 28.6139, 'longitude': 77.2090},  # Delhi coordinates
            color_scheme='light',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )
        
        # Scrape all URLs concurrently
        tasks = [scrape_tab(context, cat, url) for cat, url in job_urls.items()]
        all_pages_data = await asyncio.gather(*tasks)
        
        # Flatten the results
        all_job_data = [item for sublist in all_pages_data for item in sublist]
        
        # Display the data in the terminal
        if all_job_data:
            df = pd.DataFrame(all_job_data)
            
            # Settings to show ALL columns and rows in terminal
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 2000)
            pd.set_option('display.max_colwidth', None)
            
            print("\n" + "="*80)
            print(f"FOUND {len(all_job_data)} JOBS")
            print("="*80 + "\n")
            print(df)
        else:
            print("No job data found. Check the site structure or your selectors or block status")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())