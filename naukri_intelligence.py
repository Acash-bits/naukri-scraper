import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import pandas as pd
from bs4 import BeautifulSoup
import random
import mysql.connector
from mysql.connector import Error
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv


load_dotenv() # Load Environment variables from .env files


# Database Configuration
DB_CONFIG = {
    'host': os.getenv('HOST'),
    'user': os.getenv('USER'),
    'password': os.getenv('PASS'),
    'database': os.getenv('DATABASE')
}

# Email Configuration
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', '587')),
    'sender_email': os.getenv('SENDER_EMAIL'),
    'sender_password': os.getenv('SENDER_PASSWORD'),
    'recipient_email': os.getenv('RECIPIENT_EMAIL')
}

def init_db_mysql():
    '''Initialize the MYSQL database and Table'''
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor=conn.cursor()
        print("Connection with database has been established successfully")
    except Error as e:
        print(f'Error while establishing the connection with MySQL: {e}')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


job_urls = {
    'Business Analyst': 'https://www.naukri.com/business-analyst-jobs-in-delhi-ncr?k=business+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Senior Business Analyst': 'https://www.naukri.com/senior-business-analyst-jobs-in-delhi-ncr?k=senior+business+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Data Analyst': 'https://www.naukri.com/data-analyst-jobs-in-delhi-ncr?k=data+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Product Manager': 'https://www.naukri.com/product-manager-jobs-in-delhi-ncr?k=product+manager&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Strategy Analyst': 'https://www.naukri.com/strategy-analyst-jobs-in-delhi-ncr?k=strategy%20analyst&l=delhi%20%2F%20ncr%2C%20noida%2C%20gurugram&experience=4&nignbevent_src=jobsearchDeskGNB'
}

# CONFIGURE HOW MANY PAGES TO SCRAPE
MAX_PAGES = 50  # Set to desired number of pages to scrape per category

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


def save_job_to_mysql(job_list):
    """Inserts a job record to MySQL, ignoring duplicates based on URL"""
    if not job_list:
        return

    conn = None # Initiliaze to avoid errors in 'finally' if connection fails

    try:
        conn=mysql.connector.connect(**DB_CONFIG)
        cursor=conn.cursor()

        # Query to insert the data in batch
        query = """
            INSERT IGNORE INTO job_postings
            (category, Job_title, company_name, location, salary, experience, posting_time, time_category, link, page_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        
        # Converting list of dictonaries to a list of tuples (which MySQL expects)
        data_to_insert = [
            (
            j['Category'],
            j['Title'],
            j['Company'],
            j['Location'],
            j['Salary'],
            j['Experience'],
            j['Posted'],
            j['Time Category'],
            j['Link'],
            j['Page'])
            for j in job_list
        ]
        # Insert the data using batch insert
        cursor.executemany(query, data_to_insert)
        conn.commit()
        print(f'Successfully saved {cursor.rowcount} new jobs to the database.')
    
    # Error handling, printing the error that might get encountered while running the code
    except Error as e:
        print(f'Database insert error: {e}')
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def get_unsent_jobs():
    """Fetch all jobs where email_sent = 0"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query =''' 
            SELECT job_id, category, job_title, company_name, location, 
                   salary, experience, posting_time, time_category, link
            FROM job_postings
            WHERE email_sent = 0
            ORDER BY created_at DESC
            '''
        cursor.execute(query)
        unsent_jobs = cursor.fetchall()

        print(f"Found {len(unsent_jobs)} unsent jobs in database")
        return unsent_jobs
    except Error as e:
        print(f'Error fetching unsent jobs: {e}')
        return[]
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def create_email_html(jobs):
    """Create a nicely formatted HTML email with job listings"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 30px;
            }}
            .job-card {{
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }}
            .job-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }}
            .job-title {{
                color: #667eea;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .company {{
                color: #555;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 10px;
            }}
            .detail-row {{
                margin: 8px 0;
                display: flex;
                align-items: center;
            }}
            .label {{
                font-weight: 600;
                color: #666;
                min-width: 120px;
            }}
            .value {{
                color: #333;
            }}
            .badge {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-right: 8px;
            }}
            .badge-new {{
                background: #10b981;
                color: white;
            }}
            .badge-recent {{
                background: #f59e0b;
                color: white;
            }}
            .badge-old {{
                background: #6b7280;
                color: white;
            }}
            .apply-btn {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin-top: 15px;
            }}
            .footer {{
                text-align: center;
                color: #666;
                padding: 20px;
                margin-top: 30px;
                border-top: 2px solid #e0e0e0;
            }}
            .category-tag {{
                background: #f3f4f6;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 13px;
                color: #4b5563;
                font-weight: 600;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 New Job Opportunities</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">
                {len(jobs)} new job{'' if len(jobs) == 1 else 's'} matching your preferences
            </p>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">
                {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </p>
        </div>
    """
    
    for idx, job in enumerate(jobs, 1):
        # Determine badge color based on time category
        badge_class = 'badge-old'
        if job['time_category'] == 'Posted Just Now':
            badge_class = 'badge-new'
        elif job['time_category'] == 'Recently Posted':
            badge_class = 'badge-recent'
        
        html += f"""
        <div class="job-card">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                <div>
                    <div class="job-title">{job['job_title']}</div>
                    <div class="company">{job['company_name']}</div>
                </div>
                <span class="category-tag">{job['category']}</span>
            </div>
            
            <div class="detail-row">
                <span class="label">📍 Location:</span>
                <span class="value">{job['location']}</span>
            </div>
            
            <div class="detail-row">
                <span class="label">💼 Experience:</span>
                <span class="value">{job['experience']}</span>
            </div>
            
            <div class="detail-row">
                <span class="label">💰 Salary:</span>
                <span class="value">{job['salary']}</span>
            </div>
            
            <div class="detail-row">
                <span class="label">⏰ Posted:</span>
                <span class="badge {badge_class}">{job['time_category']}</span>
                <span class="value" style="font-size: 13px; color: #666;">({job['posting_time']})</span>
            </div>
            
            <a href="{job['link']}" class="apply-btn" target="_blank">
                View Job Details →
            </a>
        </div>
        """
    
    html += """
        <div class="footer">
            <p><strong>Job Alert System</strong></p>
            <p style="font-size: 14px; color: #888; margin-top: 10px;">
                You're receiving this email because you subscribed to job alerts.<br>
                Jobs are automatically scraped from Naukri.com for Delhi NCR region.
            </p>
        </div>
    </body>
    </html>
    """
    
    return html

def send_job_emails(jobs):
    """Send Email with job listing"""
    if not jobs:
        print('No new jobs in the databse to send')
        return False
    
    try:
        # Validate email configuration
        if not all([EMAIL_CONFIG['sender_email'], 
                    EMAIL_CONFIG['sender_password'], 
                    EMAIL_CONFIG['recipient_email']]):
            print('Error configuring the email. Please check the .env (environment) file')
            return False
        
        # Create Message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'{len(jobs)} New Jobs {"s" if len(jobs) > 1 else " "} Alert - {datetime.now().strftime("%B %d, %Y")}'
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = EMAIL_CONFIG['recipient_email']

        # Create HTML Content
        html_content = create_email_html(jobs)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        # Send Email
        print(f" Connecting to STMP Server: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")

        with smtplib.SMTP(EMAIL_CONFIG('smtp_server'), EMAIL_CONFIG('smtp_port')) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)

        print('===='*80)
        print(f'Email sent successfully to {EMAIL_CONFIG["recipient_email"]} with {len(jobs)} job listings!')
        print('===='*80)
    except Exception as e:
        print(f'Error sending email: {e}')
        return False

def mark_jobs_as_sent(job_ids):
    '''Mark jobs as sent(email_sent = 1) in database'''
    if not job_ids:
        return
    
    conn = None
    try:
        conn=mysql.connector.connect(**DB_CONFIG)
        cursor= conn.cursor()

        # Update multi jobs at once
        placeholders = ','.join(['%s']) * len(job_ids)
        query = f'Update job_postings SET email_sent = 1 where id in ({placeholders})'

        cursor.execute(query,job_ids)
        conn.commit()

        print(f'Marked {cursor.rowcount} jobs as sent in database')
    except Error as e:
        print(f'Error updating the jobs as sent: {e}')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

def process_and_send_emails():
    '''Main function to fetch unsent jobs and send them via email'''
    print('\n' + '='*80)
    print('PROCESSING EMAIL NOTIFICATIONS')
    print("="*80 + "\n")

    # Get unsent jobs
    unsent_jobs = get_unsent_jobs()
    if not unsent_jobs:
        print('No unsent jobs found. All caught up!!!!')
        return
    
    print(f'\n Preparing to send {len(unsent_jobs)} job(s) via email.....')
    
    #Send Email
    email_sent = send_job_emails(unsent_jobs)

    if email_sent:
        # Marks jobs as sent
        job_ids = [job['id'] for job in unsent_jobs]
        mark_jobs_as_sent(job_ids)

        print('\nEmail process completed sucessfully!!')
    else:
        print('\nEmail sending failed. Jobs remain marked as unsent')

    print("\n" + "=" * 80 + "\n")

async def main():
    init_db_mysql()

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
            print("Saving data to MySQL......")
            save_job_to_mysql(all_job_data)

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

    # After scraping, process and send emails for unsent jobs
    process_and_send_emails()

if __name__ == "__main__":
    asyncio.run(main())