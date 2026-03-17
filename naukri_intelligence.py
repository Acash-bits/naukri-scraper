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
import schedule
import time
from dotenv import load_dotenv


load_dotenv()  # Load Environment variables from .env file


# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

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

# Job Search URLs — add or remove categories here
job_urls = {
    'Strategy Analyst':        'https://www.naukri.com/strategy-analyst-jobs-in-delhi-ncr?k=strategy%20analyst&l=delhi%20%2F%20ncr%2C%20noida%2C%20gurugram&experience=4&nignbevent_src=jobsearchDeskGNB',
    'Strategy Manager':         'https://www.naukri.com/strategy-manager-jobs-in-delhi-ncr?k=strategy%20manager&l=delhi%20%2F%20ncr%2C%20gurugram%2C%20noida&experience=4&nignbevent_src=jobsearchDeskGNB',
    'Business Analyst':        'https://www.naukri.com/business-analyst-jobs-in-delhi-ncr?k=business+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Senior Business Analyst': 'https://www.naukri.com/senior-business-analyst-jobs-in-delhi-ncr?k=senior+business+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
    'Data Analyst':            'https://www.naukri.com/data-analyst-jobs-in-delhi-ncr?k=data+analyst&l=delhi+%2F+ncr%2C+gurugram%2C+noida&experience=4',
}

# Scraping parameters
MAX_PAGES = 50               # Max pages to scrape per category
SCRAPE_INTERVAL_HOURS = 3    # Hours between scheduled runs
RUN_IMMEDIATELY = True       # Run on startup or wait for first interval

# Category colour map for email gradients (hex values, no #)
# Add a new entry here whenever you add a new category to job_urls
CATEGORY_COLORS = {
    'Strategy Manager':         ('43e97b', '38f9d7'),   # green-teal
    'Strategy Analyst':        ('fa709a', 'fee140'),   # pink-yellow
    'Business Analyst':        ('667eea', '764ba2'),   # purple
    'Senior Business Analyst': ('f093fb', 'f5576c'),   # pink-red
    'Data Analyst':            ('4facfe', '00f2fe'),   # blue-cyan
}
DEFAULT_COLORS = ('667eea', '764ba2')


# ─────────────────────────────────────────────────────────────
# DATABASE FUNCTIONS
# ─────────────────────────────────────────────────────────────

def init_db_mysql():
    """Initialize the MySQL database connection (smoke test)"""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = conn.cursor()
        print("Connection with database has been established successfully")
    except Error as e:
        print(f'Error while establishing the connection with MySQL: {e}')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def save_job_to_mysql(job_list):
    """Insert job records into MySQL, ignoring duplicates based on URL"""
    if not job_list:
        return

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        query = """
            INSERT IGNORE INTO job_postings
            (category, job_title, company_name, location, salary, experience,
             posting_time, time_category, link, page_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

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
                j['Page']
            )
            for j in job_list
        ]

        cursor.executemany(query, data_to_insert)
        conn.commit()
        print(f'Successfully saved {cursor.rowcount} new jobs to the database.')

    except Error as e:
        print(f'Database insert error: {e}')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def get_unsent_jobs():
    """
    Fetch all jobs where email_sent = 0, grouped by category.
    Returns a dict:  { 'Business Analyst': [...], 'Data Analyst': [...], ... }
    """
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        query = '''
            SELECT job_id, category, job_title, company_name, location,
                   salary, experience, posting_time, time_category, link, scraped_time
            FROM job_postings
            WHERE email_sent = 0
            ORDER BY category, scraped_time DESC
        '''
        cursor.execute(query)
        all_unsent = cursor.fetchall()

        # Group by category into a dict
        grouped = {}
        for job in all_unsent:
            cat = job['category']
            grouped.setdefault(cat, []).append(job)

        total = sum(len(v) for v in grouped.values())
        print(f"Found {total} unsent jobs across {len(grouped)} category/categories in database")
        return grouped

    except Error as e:
        print(f'Error fetching unsent jobs: {e}')
        return {}
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


def mark_jobs_as_sent(job_ids):
    """Mark jobs as sent (email_sent = 1) in database"""
    if not job_ids:
        return

    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        placeholders = ','.join(['%s'] * len(job_ids))
        query = f'UPDATE job_postings SET email_sent = 1 WHERE job_id IN ({placeholders})'

        cursor.execute(query, job_ids)
        conn.commit()
        print(f'Marked {cursor.rowcount} jobs as sent in database')

    except Error as e:
        print(f'Error updating jobs as sent: {e}')
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# ─────────────────────────────────────────────────────────────
# SCRAPING FUNCTIONS
# ─────────────────────────────────────────────────────────────

def categorize_posting_time(posted_text):
    """Categorize job posting time into defined buckets"""
    if not posted_text or posted_text == 'N/A':
        return 'N/A'

    posted_text_lower = posted_text.lower()

    just_now_keywords = ['hour', 'just now', 'hours']
    if any(keyword in posted_text_lower for keyword in just_now_keywords):
        return 'Posted Just Now'

    within_days_keywords = ['today', '1 day', '2 days']
    if any(keyword in posted_text_lower for keyword in within_days_keywords):
        return 'Recently Posted'

    recent_keywords = ['3 days', '4 days']
    if any(keyword in posted_text_lower for keyword in recent_keywords):
        return 'Posted Within 3 - 4 days'

    within_week_keywords = ['5 days', '6 days', '7 days']
    if any(keyword in posted_text_lower for keyword in within_week_keywords):
        return 'Posted This Week'

    return 'Old'


async def human_like_behavior(page):
    """Simulate human-like mouse movements and scrolling"""
    try:
        for _ in range(random.randint(2, 4)):
            await page.mouse.wheel(0, random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.5, 1.5))

        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 2)')
        await asyncio.sleep(random.uniform(1, 2))

        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(random.uniform(1, 2))

        await page.evaluate('window.scrollTo(0, document.body.scrollHeight / 3)')
        await asyncio.sleep(random.uniform(0.5, 1))
    except Exception as e:
        print(f"⚠️ Human behavior simulation error: {e}")


async def scrape_current_page(page, category, page_num):
    """Scrape job listings from the current page"""
    try:
        await page.wait_for_selector('div.srp-jobtuple-wrapper', timeout=10000)
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')

        if not job_cards:
            print(f"⚠️ No job cards found on page {page_num}")
            return []

        page_results = []

        for job in job_cards:
            title_tag      = job.find('a', class_='title')
            company_tag    = job.find('a', class_='comp-name')
            experience_tag = job.find('span', class_='exp-wrap')
            location_tag   = job.find('span', class_='loc-wrap')
            posting_tag    = job.find('span', class_='job-post-day')
            salary_tag     = job.find('span', class_='sal-wrap')

            if title_tag:
                time_category = categorize_posting_time(
                    posting_tag.text.strip() if posting_tag else 'N/A'
                )

                if time_category != 'Old':
                    job_dict = {
                        'Category':      category,
                        'Page':          page_num,
                        'Title':         title_tag.text.strip() if title_tag else 'N/A',
                        'Company':       company_tag.text.strip() if company_tag else 'N/A',
                        'Experience':    experience_tag.text.strip() if experience_tag else 'N/A',
                        'Location':      location_tag.text.strip() if location_tag else 'N/A',
                        'Salary':        salary_tag.text.strip() if salary_tag else 'N/A',
                        'Time Category': time_category,
                        'Posted':        posting_tag.text.strip() if posting_tag else 'N/A',
                        'Link':          title_tag.get('href', 'N/A')
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
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
        await asyncio.sleep(random.uniform(1, 2))

        next_selectors = [
            'a.styles_btn-secondary__2AsIP:has-text("Next")',
            'a.styles_btn-secondary__2AsIP span:has-text("Next")',
            'a:has-text("Next")',
        ]

        next_button = None

        for selector in next_selectors:
            try:
                next_button = await page.query_selector(selector)
                if next_button:
                    tag_name = await next_button.evaluate('el => el.tagName')
                    if tag_name.lower() == 'a':
                        print(f"🔍 Found Next button using selector: {selector}")
                        break
                    elif tag_name.lower() == 'span':
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

        await next_button.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.5, 1.5))

        try:
            await next_button.hover()
            await asyncio.sleep(random.uniform(0.3, 0.7))
        except:
            pass

        await next_button.click()
        print(f"🖱️ Clicked Next button successfully")

        await page.wait_for_load_state('networkidle', timeout=30000)
        await asyncio.sleep(random.uniform(3, 5))

        return True

    except Exception as e:
        print(f"⚠️ Error clicking Next button: {e}")
        return False


async def scrape_tab(context, category, base_url, max_pages, visit_homepage=True):
    """Scrape multiple pages for a single job category by clicking Next"""
    page = await context.new_page()

    stealth_config = Stealth()
    await stealth_config.apply_stealth_async(page)

    print(f"🚀 Scraping: {category} (Up to {max_pages} pages)")
    all_results = []

    try:
        if visit_homepage:
            print(f"  🌐 Visiting homepage to establish session...")
            await page.goto('https://www.naukri.com/', wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))

            try:
                close_buttons = await page.query_selector_all(
                    'button[class*="close"], div[class*="close"], span[class*="close"]'
                )
                for btn in close_buttons[:3]:
                    try:
                        await btn.click(timeout=2000)
                        await asyncio.sleep(0.5)
                    except:
                        pass
            except:
                pass

        print(f"📄 Navigating to starting page...")
        await page.goto(base_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(random.uniform(3, 5))

        page_num = 1

        while page_num <= max_pages:
            print(f"📄 Scraping Page {page_num}...")
            current_url = page.url
            print(f"URL: {current_url}")

            await human_like_behavior(page)

            page_results = await scrape_current_page(page, category, page_num)
            all_results.extend(page_results)

            if page_num >= max_pages:
                print(f"ℹ️ Reached max pages limit ({max_pages})")
                break

            delay = random.uniform(5, 10)
            print(f'⏳ Waiting {delay:.1f}s before clicking Next...')
            await asyncio.sleep(delay)

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


# ─────────────────────────────────────────────────────────────
# EMAIL FUNCTIONS
# ─────────────────────────────────────────────────────────────

def create_email_html(jobs, category='All Jobs'):
    """
    Generate a beautifully formatted HTML email for ONE category.
    Each category gets its own unique gradient colour scheme.
    """
    c1, c2 = CATEGORY_COLORS.get(category, DEFAULT_COLORS)
    gradient = f"linear-gradient(135deg, #{c1} 0%, #{c2} 100%)"

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
                background-color: #f5f5f5;
            }}
            .header {{
                background: {gradient};
                color: white;
                padding: 30px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 20px;
            }}
            .jobs-container {{
                max-height: 600px;
                overflow-y: auto;
                overflow-x: hidden;
                padding: 15px;
                background: #fafafa;
                border-radius: 10px;
                border: 2px solid #e0e0e0;
                margin-bottom: 20px;
            }}
            .jobs-container::-webkit-scrollbar {{ width: 12px; }}
            .jobs-container::-webkit-scrollbar-track {{
                background: #f1f1f1;
                border-radius: 10px;
            }}
            .jobs-container::-webkit-scrollbar-thumb {{
                background: {gradient};
                border-radius: 10px;
            }}
            .scroll-indicator {{
                text-align: center;
                padding: 10px;
                background: #fff3cd;
                border-radius: 8px;
                margin-bottom: 15px;
                color: #856404;
                font-weight: 600;
                border: 1px solid #ffeaa7;
            }}
            .job-card {{
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 15px;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }}
            .job-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }}
            .job-title  {{ color: #{c1}; font-size: 20px; font-weight: bold; margin-bottom: 10px; }}
            .company    {{ color: #555; font-size: 16px; font-weight: 600; margin-bottom: 10px; }}
            .detail-row {{ margin: 8px 0; display: flex; align-items: center; }}
            .label      {{ font-weight: 600; color: #666; min-width: 120px; }}
            .value      {{ color: #333; }}
            .badge      {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 600;
                margin-right: 8px;
            }}
            .badge-new     {{ background: #10b981; color: white; }}
            .badge-recent  {{ background: #f59e0b; color: white; }}
            .badge-week    {{ background: #8b5cf6; color: white; }}
            .badge-old     {{ background: #6b7280; color: white; }}
            .badge-scraped {{ background: #3b82f6; color: white; }}
            .apply-btn {{
                display: inline-block;
                background: {gradient};
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                font-weight: 600;
                margin-top: 15px;
            }}
            .apply-btn:hover {{ opacity: 0.9; }}
            .category-tag {{
                background: #f3f4f6;
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 13px;
                color: #4b5563;
                font-weight: 600;
            }}
            .stats-bar {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                text-align: center;
                border: 1px solid #e0e0e0;
            }}
            .footer {{
                text-align: center;
                color: #666;
                padding: 20px;
                border-top: 2px solid #e0e0e0;
                background: white;
                border-radius: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 {category}</h1>
            <p style="margin: 10px 0 0 0; font-size: 18px;">
                {len(jobs)} new job{'s' if len(jobs) != 1 else ''} found in Delhi NCR
            </p>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.9;">
                {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </p>
        </div>

        <div class="stats-bar">
            <strong>📊 Total {category} Jobs: {len(jobs)}</strong>
            <span style="margin: 0 15px;">|</span>
            <span style="color: #10b981;">● Just Now</span>
            <span style="margin: 0 15px;">|</span>
            <span style="color: #f59e0b;">● Recent</span>
            <span style="margin: 0 15px;">|</span>
            <span style="color: #8b5cf6;">● This Week</span>
        </div>

        <div class="scroll-indicator">
            ⬇️ Scroll to see all {len(jobs)} {category} listings ⬇️
        </div>

        <div class="jobs-container">
    """

    for idx, job in enumerate(jobs, 1):
        time_cat = job.get('time_category', '')
        if time_cat == 'Posted Just Now':
            badge_class = 'badge-new'
        elif time_cat == 'Recently Posted':
            badge_class = 'badge-recent'
        elif time_cat in ('Posted Within 3 - 4 days', 'Posted This Week'):
            badge_class = 'badge-week'
        else:
            badge_class = 'badge-old'

        scraped_time = job.get('scraped_time')
        if scraped_time:
            if isinstance(scraped_time, str):
                scraped_time = datetime.strptime(scraped_time, '%Y-%m-%d %H:%M:%S')
            scraped_time_str = scraped_time.strftime('%B %d, %Y at %I:%M %p')
        else:
            scraped_time_str = 'N/A'

        html += f"""
            <div class="job-card">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 15px;">
                    <div>
                        <div class="job-title">#{idx} - {job['job_title']}</div>
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
                    <span class="badge {badge_class}">{time_cat}</span>
                    <span class="value" style="font-size: 13px; color: #666;">({job['posting_time']})</span>
                </div>
                <div class="detail-row">
                    <span class="label">🕐 Scraped:</span>
                    <span class="badge badge-scraped">In Database</span>
                    <span class="value" style="font-size: 13px; color: #666;">{scraped_time_str}</span>
                </div>

                <a href="{job['link']}" class="apply-btn" target="_blank">
                    View Job Details →
                </a>
            </div>
        """

    html += """
        </div>
        <div class="footer">
            <p><strong>Naukri Job Alert System</strong></p>
            <p style="font-size: 14px; color: #888; margin-top: 10px;">
                Jobs automatically scraped from Naukri.com for Delhi NCR.<br>
                You are receiving this because you subscribed to job alerts.
            </p>
        </div>
    </body>
    </html>
    """
    return html


def send_job_emails(jobs, category='Jobs'):
    """
    Send one HTML email for the given category's job list.
    Subject line: [Business Analyst] 8 New Jobs Alert – Feb 22, 2026
    Returns True on success, False on failure.
    """
    if not jobs:
        print(f'No jobs to send for: {category}')
        return False

    try:
        if not all([EMAIL_CONFIG['sender_email'],
                    EMAIL_CONFIG['sender_password'],
                    EMAIL_CONFIG['recipient_email']]):
            print('Email configuration missing. Check your .env file.')
            return False

        msg = MIMEMultipart('alternative')
        msg['Subject'] = (
            f"[{category}] {len(jobs)} New Job{'s' if len(jobs) != 1 else ''} "
            f"Alert - {datetime.now().strftime('%B %d, %Y')}"
        )
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To']   = EMAIL_CONFIG['recipient_email']

        html_content = create_email_html(jobs, category)
        msg.attach(MIMEText(html_content, 'html'))

        print(f"  📤 Connecting to SMTP for [{category}]...")
        with smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port']) as server:
            server.starttls()
            server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
            server.send_message(msg)

        print('=' * 80)
        print(f"  ✅ Email sent for [{category}] → {len(jobs)} jobs to {EMAIL_CONFIG['recipient_email']}")
        print('=' * 80)
        return True

    except Exception as e:
        print(f'  ❌ Error sending email for [{category}]: {e}')
        return False


def process_and_send_emails():
    """
    Fetches unsent jobs grouped by category, sends a SEPARATE email for each
    category, then marks all successfully emailed jobs as sent.
    """
    print('\n' + '=' * 80)
    print('PROCESSING EMAIL NOTIFICATIONS  (one email per category)')
    print('=' * 80 + '\n')

    # Returns dict: { 'Business Analyst': [...], 'Data Analyst': [...], ... }
    grouped_jobs = get_unsent_jobs()

    if not grouped_jobs:
        print('No unsent jobs found. All caught up!')
        return

    successfully_sent_ids = []

    for category, jobs in grouped_jobs.items():
        print(f'\n── Category: {category} ({len(jobs)} jobs) ──')
        success = send_job_emails(jobs, category)
        if success:
            successfully_sent_ids.extend([job['job_id'] for job in jobs])
        else:
            print(f'  ⚠️  Skipping mark-as-sent for [{category}] — will retry next run.')

    # Mark only the jobs whose emails were successfully sent
    if successfully_sent_ids:
        mark_jobs_as_sent(successfully_sent_ids)

    total_attempted = sum(len(v) for v in grouped_jobs.values())
    total_failed    = total_attempted - len(successfully_sent_ids)

    print('\n' + '=' * 80)
    print('EMAIL SUMMARY')
    print(f'  Categories processed : {len(grouped_jobs)}')
    print(f'  Jobs marked sent     : {len(successfully_sent_ids)}')
    if total_failed:
        print(f'  Jobs NOT sent        : {total_failed}  <- will retry next run')
    print('=' * 80 + '\n')


# ─────────────────────────────────────────────────────────────
# DISPLAY / UTILITY
# ─────────────────────────────────────────────────────────────

def print_job_details(all_job_data):
    """Print job details in formatted console output"""
    print("\n" + "=" * 80)
    print(f"FOUND {len(all_job_data)} JOBS")
    print("=" * 80 + "\n")

    for idx, job in enumerate(all_job_data, 1):
        print(f"\n{'─' * 80}")
        print(f"JOB #{idx}")
        print(f"{'─' * 80}")
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


# ─────────────────────────────────────────────────────────────
# MAIN ASYNC FUNCTION
# ─────────────────────────────────────────────────────────────

async def main():
    init_db_mysql()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--headless=new',  # Comment this out to see the browser window
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1366, 'height': 768},
            locale='en-US',
            timezone_id='Asia/Kolkata',
            permissions=['geolocation'],
            geolocation={'latitude': 28.6139, 'longitude': 77.2090},
            color_scheme='light',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
        )

        # ── OPTION 1: CONCURRENT (faster, higher bot-detection risk) ──────────
        tasks = [scrape_tab(context, cat, url, MAX_PAGES) for cat, url in job_urls.items()]
        all_pages_data = await asyncio.gather(*tasks)
        all_job_data = [item for sublist in all_pages_data for item in sublist]

        # ── OPTION 2: SEQUENTIAL (safer, slower) ─────────────────────────────
        # Uncomment the block below and comment out OPTION 1 above if you get blocked.
        #
        # print("🚀 Starting SEQUENTIAL scraping (one category at a time)...\n")
        # all_job_data = []
        # for i, (cat, url) in enumerate(job_urls.items()):
        #     visit_home = (i == 0)
        #     results = await scrape_tab(context, cat, url, MAX_PAGES, visit_homepage=visit_home)
        #     all_job_data.extend(results)
        #     if i < len(job_urls) - 1:
        #         delay = random.uniform(15, 25)
        #         print(f"⏸️  Waiting {delay:.1f}s before next category...\n")
        #         await asyncio.sleep(delay)

        if all_job_data:
            pd.set_option('display.max_rows', None)
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', 2000)
            pd.set_option('display.max_colwidth', None)

            print_job_details(all_job_data)
            print("Saving data to MySQL......")
            save_job_to_mysql(all_job_data)

            df = pd.DataFrame(all_job_data)
            print('\n' + "=" * 80 + "\n")
            print('Summary by Category:')
            print(df.groupby('Category').size())
            print('\n' + "=" * 80 + "\n")
        else:
            print("No job data found. Check the site structure, selectors, or block status.")

        await browser.close()

    # After scraping, send one separate email per category for all unsent jobs
    process_and_send_emails()


# ─────────────────────────────────────────────────────────────
# SCHEDULER
# ─────────────────────────────────────────────────────────────

def run_scraper():
    """Wrapper to run the scraper with timestamps and error handling"""
    print("\n" + "🔄" * 40)
    print(f"Starting scheduled scrape at {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}")
    print("🔄" * 40 + "\n")

    try:
        asyncio.run(main())
        print("\n" + "✅" * 40)
        print(f"Scrape completed at {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}")
        print("✅" * 40 + "\n")
    except Exception as e:
        print(f"\n❌ Error during scheduled scrape: {e}\n")


if __name__ == "__main__":
    print("=" * 80)
    print("🤖 JOB SCRAPER SCHEDULER STARTED")
    print("=" * 80)
    print(f"⏰ Scraper will run every {SCRAPE_INTERVAL_HOURS} hour(s)")
    print(f"🕐 Current time: {datetime.now().strftime('%B %d, %Y at %I:%M:%S %p')}")
    print("=" * 80 + "\n")

    schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(run_scraper)

    if RUN_IMMEDIATELY:
        run_scraper()

    print("⏳ Waiting for next scheduled run...\n")
    while True:
        schedule.run_pending()
        time.sleep(60)