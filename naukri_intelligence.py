import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import pandas as pd
from bs4 import BeautifulSoup
import random

job_urls = {
    'Business Analyst': 'https://www.naukri.com/business-analyst-jobs-in-delhi-ncr?k=business+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Senior Business Analyst': 'https://www.naukri.com/senior-business-analyst-jobs-in-delhi-ncr?k=senior+business+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Data Analyst': 'https://www.naukri.com/data-analyst-jobs-in-delhi-ncr?k=data+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Product Manager': 'https://www.naukri.com/product-manager-jobs-in-delhi-ncr?k=product+manager&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Strategy Analyst': 'https://www.naukri.com/strategy-analyst-jobs-in-delhi-ncr?k=strategy%20analyst&l=delhi%20%2F%20ncr%2C%20noida%2C%20gurugram&experience=4&nignbevent_src=jobsearchDeskGNB'
}

# CONFIGURE HOW MANY PAGES TO SCRAPE
MAX_PAGES = 2  # Set to desired number of pages to scrape per category

def categorize_posting_time(posted_text):
    """Categorize job posting time into defined buckets"""
    if not posted_text or posted_text == 'N/A':
        return 'N/A'
    
    posted_text_lower = posted_text.lower()

    # Just now cateogry: Up to 2 days
    just_now_keywords = ['hour', 'today', 'just now', '1 day', '2 days']
    if any(keyword in posted_text_lower for keyword in just_now_keywords):
        return 'Posted Just Now'
    
    # Recent Category: 3 to 7 days (1 Week)
    recent_keywords = ['3 days', '4 days', '5 days', '6 days', '7 days', '1 week']
    if any(keyword in posted_text_lower for keyword in recent_keywords):
        return 'Recently Posted'
    
    # Old category: Includes everytime that is after the above mentioned ones
    return 'Old'



async def human_like_behavior(page):
    """Simulate human-like mouse movements and scrolling"""
    try:
        # Random small scrolls
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Scroll to middle
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
        await asyncio.sleep(random.uniform(1, 2))
        
        # Scroll to bottom
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(random.uniform(1, 2))
        
        # Scroll back up a bit
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 3)')
        await asyncio.sleep(random.uniform(0.5, 1))
    except Exception as e:
        print(f"⚠️ Human behavior simulation error: {e}")

async def scrape_current_page(page, category, page_num):
    """Scrape job listings from the current page"""
    try:
        # Wait for job listings to load
        await page.wait_for_selector('div.srp-jobtuple-wrapper', timeout=10000)
        
        # Get the page HTML content
        html_content = await page.content()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
        
        if not job_cards:
            print(f"⚠️ No job cards found on page {page_num}")
            return []
        
        page_results = []
        
        for job in job_cards:
            # Job Title
            title_tag = job.find('a', class_='title')
            # Company Name
            company_tag = job.find('a', class_='comp-name')
            # Experience for the job
            experience_tag = job.find('span', class_='exp-wrap')
            # Location of the job
            location_tag = job.find('span', class_='loc-wrap')
            # Job Posting Time
            posting_tag = job.find('span', class_='job-post-day')
            # Salary Range
            salary_tag = job.find('span', class_='sal-wrap')
            
            if title_tag:
                # Categorizing posting time
                time_category = categorize_posting_time(posting_tag.text.strip() if posting_tag else 'N/A')
                
                job_dict = {
                    'Category': category,
                    'Page': page_num,
                    'Title': title_tag.text.strip() if title_tag else 'N/A',
                    'Company': company_tag.text.strip() if company_tag else 'N/A',
                    'Experience': experience_tag.text.strip() if experience_tag else 'N/A',
                    'Location': location_tag.text.strip() if location_tag else 'N/A',
                    'Salary': salary_tag.text.strip() if salary_tag else 'N/A',
                    'Time Category': time_category,
                    'Posted': posting_tag.text.strip() if posting_tag else 'N/A',
                    'Link': title_tag.get('href', 'N/A')
                }
                page_results.append(job_dict)
        
        print(f"✅ Found {len(page_results)} jobs on page {page_num}")
        return page_results
        
    except Exception as e:
        print(f"      ⚠️ Error scraping page {page_num}: {e}")
        return []

async def click_next_button(page):
    """Click the Next button to navigate to the next page"""
    try:
        # Scroll to pagination area first
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(random.uniform(1, 2))
        
        # Target the specific Next button element from Naukri
        # <a href="/business-analyst-jobs-in-delhi-ncr-3" class="styles_btn-secondary__2AsIP"><span>Next</span><i class="ni-icon-arrow-2"></i></a>
        next_selectors = [
            'a.styles_btn-secondary__2AsIP:has-text("Next")',  # Primary selector - Naukri's Next button
            'a.styles_btn-secondary__2AsIP span:has-text("Next")',  # Target the span inside
            'a:has-text("Next")',  # Fallback: any link with "Next" text
        ]
        
        next_button = None
        
        # Try each selector
        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    # Verify it's actually a clickable link element
                    tag_name = await next_button.evaluate('el => el.tagName')
                    if tag_name.lower() == 'a':
                        print(f"🔍 Found Next button using selector: {selector}")
                        break
                    elif tag_name.lower() == 'span':
                        # If we found the span, get its parent <a> tag
                        next_button = await next_button.evaluate_handle('el => el.parentElement')
                        print(f"🔍 Found Next button (via span parent)")
                        break
                    else:
                        next_button = None
            except Exception as e:
                print(f"      ⚠️ Selector '{selector}' failed: {e}")
                continue
        
        if not next_button:
            print(f"      ⚠️ Next button not found - reached last page")
            return False
        
        # Scroll the Next button into view
        await next_button.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Hover over the button first (more human-like)
        try:
            await next_button.hover()
            await asyncio.sleep(random.uniform(0.3, 0.7))
        except:
            pass
        
        # Click the Next button
        await next_button.click()
        print(f"🖱️ Clicked Next button successfully")
        
        # Wait for navigation to complete
        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(random.uniform(3, 5))
        
        return True
        
    except Exception as e:
        print(f"⚠️ Error clicking Next button: {e}")
        return False


async def scrape_tab(context, category, base_url, max_pages, visit_homepage=True):
    """Scrapes multiple pages for a single job category by clicking Next"""
    page = await context.new_page()
    
    # Apply stealth
    stealth_config = Stealth()
    await stealth_config.apply_stealth_async(page)
    
    print(f"🚀 Scraping: {category} (Up to {max_pages} pages)")

    all_results = []
    
    try:
        # Optional: visit homepage to establish session (recommended for first category)
        if visit_homepage:
            print(f"  🌐 Visiting homepage to establish session...")
            await page.goto('https://www.naukri.com/', wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Try to close any popups/modals
            try:
                close_buttons = await page.query_selector_all('button[class*="close"], div[class*="close"], span[class*="close"]')
                for btn in close_buttons[:3]:
                    try:
                        await btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                    except:
                        pass
            except:
                pass
        
        # Navigate to the first page
        print(f"📄 Navigating to starting page...")
        await page.goto(base_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(random.uniform(3, 5))
        
        # Scrape pages using Next button
        page_num = 1
        
        while page_num <= max_pages:
            print(f"📄 Scraping Page {page_num}...")
            current_url = page.url
            print(f"URL: {current_url}")
            
            # Simulate human behavior
            await human_like_behavior(page)
            
            # Scrape current page
            page_results = await scrape_current_page(page, category, page_num)
            all_results.extend(page_results)
            
            # Check if we should continue
            if page_num >= max_pages:
                print(f"ℹ️ Reached max pages limit ({max_pages})")
                break
            
            # Delay before clicking Next
            delay = random.uniform(5, 10)
            print(f'⏳ Waiting {delay:.1f}s before clicking Next...')
            await asyncio.sleep(delay)
            
            # Click Next button to go to next page
            next_clicked = await click_next_button(page)
            
            if not next_clicked:
                print(f"ℹ️ No more pages available (reached last page)")
                break
            
            page_num += 1
        
        print(f"✅ Total: {len(all_results)} jobs for {category} across {page_num} page(s)\n")
        return all_results
            
    except Exception as e:
        print(f"⚠️ Critical error in {category}: {e}")
        return all_results
    finally:
        await page.close()

def print_job_details(all_job_data):
    """Print jo details in custom format"""
    print("\n" + "="*80)
    print(f"FOUND {len(all_job_data)} JOBS")
    print("="*80 + "\n")

    for idx, job in enumerate(all_job_data, 1):
        print(f"\n{'─'*80}")
        print(f"JOB #{idx}")
        print(f"{'─'*80}")
        print(f"Job Title:       {job['Title']}")
        print(f"Company Name:    {job['Company']}")
        print(f"Experience:      {job['Experience']}")
        print(f"Location:        {job['Location']}")
        print(f"Time Category:   {job['Time Category']}")
        print(f"Posting Time:    {job['Posted']}")
        print(f"Salary:          {job['Salary']}")
        print(f"Link:            {job['Link']}")
        print(f"Page Number:     {job['Page']}")
        print(f"Category:        {job['Category']}")

async def main():
    async with async_playwright() as p:
        # Launch with additional anti-detection flags
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--headless=new', # Uncomment to run in headless mode
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
            viewport={'width': 1366, 'height': 768},
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
        tasks = [scrape_tab(context, cat, url, MAX_PAGES) for cat, url in job_urls.items()]
        all_pages_data = await asyncio.gather(*tasks)
        
        # Flatten the results
        all_job_data = [item for sublist in all_pages_data for item in sublist]
        
        # OPTION 2: SEQUENTIAL (SAFER) - One category at a time
        # Use this if: Concurrent scraping triggers bot detection
        # Uncomment below and comment out OPTION 1 above:
        
        # print("🚀 Starting SEQUENTIAL scraping (one category at a time)...\n")
        # all_job_data = []
        # for i, (cat, url) in enumerate(job_urls.items()):
        #     visit_home = (i == 0)  # Only visit homepage for first category
        #     results = await scrape_tab(context, cat, url, MAX_PAGES, visit_homepage=visit_home)
        #     all_job_data.extend(results)
        #     
        #     # Delay between categories
        #     if i < len(job_urls) - 1:
        #         delay = random.uniform(15, 25)
        #         print(f"⏸️  Waiting {delay:.1f}s before next category...\n")
        #         await asyncio.sleep(delay)

        # Display the data in the terminal
        if all_job_data:
            
            # Settings to show ALL columns and rows in terminal
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 2000)
            pd.set_option('display.max_colwidth', None)
            
            print_job_details(all_job_data)

            # Show summary by category
            df = pd.DataFrame(all_job_data)
            print('\n' + "="*80 + "\n")
            print('Summary by Category:')
            print(df.groupby('Category').size())
            print('\n' + "="*80 + "\n")
            print("\n")

            
        else:
            print("No job data found. Check the site structure or your selectors or block status")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())