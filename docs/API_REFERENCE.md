# 📖 API Reference

Complete documentation of all functions, classes, and modules in the Naukri Job Scraper.

## Table of Contents
- [Configuration](#configuration)
- [Database Functions](#database-functions)
- [Scraping Functions](#scraping-functions)
- [Email Functions](#email-functions)
- [Utility Functions](#utility-functions)
- [Main Execution](#main-execution)

---

## Configuration

### Environment Variables

Loaded from `.env` file using `python-dotenv`.

#### Database Configuration
```python
DB_CONFIG = {
    'host': str,        # MySQL server host (default: 'localhost')
    'user': str,        # MySQL username (default: 'root')
    'password': str,    # MySQL password
    'database': str     # Database name (default: 'naukri_com')
}
```

#### Email Configuration
```python
EMAIL_CONFIG = {
    'smtp_server': str,      # SMTP server (default: 'smtp.gmail.com')
    'smtp_port': int,        # SMTP port (default: 587)
    'sender_email': str,     # Sender email address
    'sender_password': str,  # Gmail app password
    'recipient_email': str   # Recipient email address
}
```

#### Job Search URLs
```python
job_urls = {
    'Category Name': 'https://www.naukri.com/...',
    # Dictionary mapping category names to search URLs
}
```

#### Scraping Parameters
```python
MAX_PAGES = 50                    # Maximum pages to scrape per category
SCRAPE_INTERVAL_HOURS = 3        # Hours between scheduled runs
RUN_IMMEDIATELY = True            # Run on startup or wait for interval
```

---

## Database Functions

### `init_db_mysql()`

Initialize MySQL database connection and verify connectivity.

**Returns:** `None`

**Side Effects:**
- Establishes connection to MySQL server
- Prints connection status
- Closes connection

**Example:**
```python
init_db_mysql()
# Output: "Connection with database has been established successfully"
```

**Exceptions:**
- `mysql.connector.Error`: If connection fails

---

### `save_job_to_mysql(job_list)`

Insert job records into MySQL database with duplicate prevention.

**Parameters:**
- `job_list` (list[dict]): List of job dictionaries to insert

**Returns:** `None`

**Side Effects:**
- Inserts jobs into `job_postings` table
- Prints number of inserted records
- Ignores duplicates (based on `link` UNIQUE constraint)

**Example:**
```python
jobs = [
    {
        'Category': 'Business Analyst',
        'Title': 'Senior BA',
        'Company': 'Tech Corp',
        'Location': 'Delhi',
        'Salary': '₹10-15 Lacs PA',
        'Experience': '4-7 Yrs',
        'Posted': '2 days ago',
        'Time Category': 'Recently Posted',
        'Link': 'https://...',
        'Page': 1
    }
]
save_job_to_mysql(jobs)
# Output: "Successfully saved 1 new jobs to the database."
```

**Database Schema:**
```sql
INSERT IGNORE INTO job_postings
(category, job_title, company_name, location, salary, 
 experience, posting_time, time_category, link, page_number)
VALUES (...)
```

---

### `get_unsent_jobs()`

Fetch all jobs where email notifications haven't been sent.

**Returns:** `list[dict]` - List of job records with `email_sent = 0`

**Example:**
```python
unsent_jobs = get_unsent_jobs()
print(f"Found {len(unsent_jobs)} unsent jobs")
# Output: "Found 25 unsent jobs in database"
```

**Returns Structure:**
```python
[
    {
        'job_id': 1,
        'category': 'Business Analyst',
        'job_title': 'Senior BA',
        'company_name': 'Tech Corp',
        'location': 'Delhi',
        'salary': '₹10-15 Lacs PA',
        'experience': '4-7 Yrs',
        'posting_time': '2 days ago',
        'time_category': 'Recently Posted',
        'link': 'https://...',
        'scraped_time': datetime(2026, 1, 17, 10, 30, 0)
    },
    # ... more jobs
]
```

---

### `mark_jobs_as_sent(job_ids)`

Update jobs to mark them as sent via email.

**Parameters:**
- `job_ids` (list[int]): List of job IDs to mark as sent

**Returns:** `None`

**Side Effects:**
- Updates `email_sent = 1` for specified job IDs
- Prints number of updated records

**Example:**
```python
job_ids = [1, 2, 3, 4, 5]
mark_jobs_as_sent(job_ids)
# Output: "Marked 5 jobs as sent in database"
```

---

## Scraping Functions

### `categorize_posting_time(posted_text)`

Categorize job posting time into defined buckets.

**Parameters:**
- `posted_text` (str): Original posting time text from Naukri.com

**Returns:** `str` - Categorized time bucket

**Time Categories:**
- `"Posted Just Now"`: Within hours, just now
- `"Recently Posted"`: Today, 1-2 days ago
- `"Posted Within 3-4 days"`: 3-4 days ago
- `"Posted This Week"`: 5-7 days ago
- `"Old"`: Older than 7 days
- `"N/A"`: If posted_text is None or 'N/A'

**Example:**
```python
categorize_posting_time("2 hours ago")     # "Posted Just Now"
categorize_posting_time("1 day ago")       # "Recently Posted"
categorize_posting_time("3 days ago")      # "Posted Within 3-4 days"
categorize_posting_time("6 days ago")      # "Posted This Week"
categorize_posting_time("10 days ago")     # "Old"
categorize_posting_time(None)              # "N/A"
```

---

### `async human_like_behavior(page)`

Simulate human-like browsing behavior to evade bot detection.

**Parameters:**
- `page` (Page): Playwright page object

**Returns:** `None`

**Side Effects:**
- Random mouse wheel scrolling (2-4 times)
- Scrolls to middle of page
- Scrolls to bottom of page
- Scrolls back up to 1/3 position
- Random delays between actions

**Example:**
```python
await human_like_behavior(page)
# Simulates realistic user scrolling and browsing
```

**Actions Performed:**
1. Random small scrolls (100-300px, 2-4 times)
2. Scroll to page middle
3. Scroll to page bottom
4. Scroll back to top third
5. Random delays (0.5-2 seconds between actions)

---

### `async scrape_current_page(page, category, page_num)`

Scrape job listings from the current page.

**Parameters:**
- `page` (Page): Playwright page object
- `category` (str): Job category name
- `page_num` (int): Current page number

**Returns:** `list[dict]` - List of scraped job dictionaries

**Example:**
```python
results = await scrape_current_page(page, "Business Analyst", 1)
print(f"Scraped {len(results)} jobs")
# Output: "✅ Found 20 jobs on page 1"
```

**Extracted Fields:**
- `Category`: Job category
- `Page`: Page number
- `Title`: Job title
- `Company`: Company name
- `Experience`: Required experience
- `Location`: Job location
- `Salary`: Salary range
- `Time Category`: Categorized posting time
- `Posted`: Original posting time text
- `Link`: Job application URL

**Filtering:**
- Excludes jobs with `Time Category == "Old"`

**HTML Selectors:**
```python
job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
title_tag = job.find('a', class_='title')
company_tag = job.find('a', class_='comp-name')
experience_tag = job.find('span', class_='exp-wrap')
location_tag = job.find('span', class_='loc-wrap')
posting_tag = job.find('span', class_='job-post-day')
salary_tag = job.find('span', class_='sal-wrap')
```

---

### `async click_next_button(page)`

Click the "Next" pagination button to navigate to next page.

**Parameters:**
- `page` (Page): Playwright page object

**Returns:** `bool`
- `True`: Successfully clicked Next button
- `False`: Next button not found (last page reached)

**Example:**
```python
success = await click_next_button(page)
if success:
    print("Navigated to next page")
else:
    print("Reached last page")
```

**Behavior:**
1. Scrolls to pagination area
2. Attempts multiple selectors to find Next button
3. Scrolls button into view
4. Hovers over button (human-like)
5. Clicks button
6. Waits for navigation to complete

**Selectors Tried (in order):**
```python
'a.styles_btn-secondary__2AsIP:has-text("Next")'
'a.styles_btn-secondary__2AsIP span:has-text("Next")'
'a:has-text("Next")'
```

---

### `async scrape_tab(context, category, base_url, max_pages, visit_homepage=True)`

Scrape multiple pages for a single job category.

**Parameters:**
- `context` (BrowserContext): Playwright browser context
- `category` (str): Job category name
- `base_url` (str): Starting URL for category
- `max_pages` (int): Maximum number of pages to scrape
- `visit_homepage` (bool): Whether to visit Naukri homepage first (default: True)

**Returns:** `list[dict]` - All scraped jobs for this category

**Example:**
```python
results = await scrape_tab(
    context,
    "Business Analyst",
    "https://www.naukri.com/business-analyst-jobs",
    max_pages=50,
    visit_homepage=True
)
print(f"Total: {len(results)} jobs")
# Output: "✅ Total: 250 jobs for Business Analyst across 50 page(s)"
```

**Process Flow:**
1. Create new page with stealth applied
2. Optionally visit homepage (session establishment)
3. Close any popups/modals
4. Navigate to category URL
5. For each page:
   - Simulate human behavior
   - Scrape current page
   - Click Next button
   - Random delay (5-10 seconds)
6. Return all results

---

## Email Functions

### `create_email_html(jobs)`

Generate beautifully formatted HTML email from job listings.

**Parameters:**
- `jobs` (list[dict]): List of job dictionaries

**Returns:** `str` - Complete HTML email string

**Example:**
```python
html = create_email_html(unsent_jobs)
# Returns full HTML email with job cards
```

**Email Features:**
- Gradient header with job count and timestamp
- Scrollable job container (max-height: 600px)
- Individual job cards with hover effects
- Color-coded badges for time categories
- Direct "View Job Details" buttons
- Professional footer

**Badge Colors:**
- `Posted Just Now`: Green (#10b981)
- `Recently Posted`: Orange (#f59e0b)
- `Old`: Gray (#6b7280)
- `In Database`: Blue (#3b82f6)

**CSS Styling:**
- Responsive layout (max-width: 900px)
- Custom scrollbar styling
- Hover effects on job cards
- Mobile-friendly design

---

### `send_job_emails(jobs)`

Send email notifications with job listings.

**Parameters:**
- `jobs` (list[dict]): List of jobs to include in email

**Returns:** `bool`
- `True`: Email sent successfully
- `False`: Email sending failed

**Example:**
```python
success = send_job_emails(unsent_jobs)
if success:
    print("Email sent!")
else:
    print("Email failed")
```

**Email Details:**
- **Subject:** `"{count} New Jobs Alert - {date}"`
- **From:** `EMAIL_CONFIG['sender_email']`
- **To:** `EMAIL_CONFIG['recipient_email']`
- **Format:** HTML (MIME multipart)

**Process:**
1. Validate email configuration
2. Create MIME message
3. Generate HTML content
4. Connect to SMTP server
5. Authenticate
6. Send message
7. Close connection

**Exceptions Handled:**
- Missing email configuration
- SMTP connection errors
- Authentication failures
- Send failures

---

### `mark_jobs_as_sent(job_ids)`

See [Database Functions](#mark_jobs_as_sentjob_ids) above.

---

### `process_and_send_emails()`

Main orchestration function for email workflow.

**Returns:** `None`

**Side Effects:**
- Fetches unsent jobs from database
- Sends email if jobs exist
- Marks jobs as sent in database
- Prints status messages

**Example:**
```python
process_and_send_emails()
# Output:
# ================================================================================
# PROCESSING EMAIL NOTIFICATIONS
# ================================================================================
# 
# Found 25 unsent jobs in database
# Preparing to send 25 job(s) via email.....
# ================================================================================
# Email sent successfully to recipient@gmail.com with 25 job listings!
# ================================================================================
# Marked 25 jobs as sent in database
# Email process completed successfully!!
```

**Workflow:**
1. Print header
2. Fetch unsent jobs (`get_unsent_jobs()`)
3. If no jobs, exit
4. Send email (`send_job_emails()`)
5. If successful, mark as sent (`mark_jobs_as_sent()`)
6. Print completion status

---

## Utility Functions

### `print_job_details(all_job_data)`

Print job details in formatted console output.

**Parameters:**
- `all_job_data` (list[dict]): List of job dictionaries

**Returns:** `None`

**Side Effects:**
- Prints formatted job listings to console

**Example:**
```python
print_job_details(all_job_data)
# Output:
# ================================================================================
# FOUND 250 JOBS
# ================================================================================
# 
# ────────────────────────────────────────────────────────────────────────────────
# JOB #1
# ────────────────────────────────────────────────────────────────────────────────
# Job Title:       Senior Business Analyst
# Company Name:    Tech Corp India
# Experience:      4-7 Yrs
# Location:        Noida
# Time Category:   Recently Posted
# Posting Time:    1 day ago
# Salary:          ₹10-15 Lacs PA
# Link:            https://...
# Page Number:     1
# Category:        Business Analyst
```

**Format:**
- Header with total count
- Separator lines
- Job number
- All job fields
- Clear visual hierarchy

---

## Main Execution

### `async main()`

Main asynchronous function orchestrating the entire scraping workflow.

**Returns:** `None`

**Side Effects:**
- Initializes database
- Launches browser
- Scrapes all job categories
- Saves to database
- Sends email notifications

**Example:**
```python
asyncio.run(main())
```

**Process Flow:**

```
┌─────────────────────────────────────────┐
│ 1. Initialize Database                  │
├─────────────────────────────────────────┤
│ 2. Launch Chromium Browser              │
│    ├── Headless mode                    │
│    ├── Anti-detection flags             │
│    └── Stealth configuration            │
├─────────────────────────────────────────┤
│ 3. Create Browser Context               │
│    ├── Realistic user agent             │
│    ├── Viewport: 1366x768               │
│    ├── Geolocation: Delhi               │
│    └── Extra HTTP headers               │
├─────────────────────────────────────────┤
│ 4. Scrape All Categories                │
│    ├── Option A: Concurrent             │
│    │   (All at once, faster)            │
│    └── Option B: Sequential             │
│        (One by one, safer)              │
├─────────────────────────────────────────┤
│ 5. Process Results                      │
│    ├── Display in console               │
│    ├── Save to MySQL                    │
│    └── Show summary by category         │
├─────────────────────────────────────────┤
│ 6. Send Email Notifications             │
│    └── process_and_send_emails()        │
├─────────────────────────────────────────┤
│ 7. Close Browser                        │
└─────────────────────────────────────────┘
```

**Browser Configuration:**
```python
browser = await p.chromium.launch(
    headless=False,  # Set to True for background operation
    args=[
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-web-security',
        '--disable-features=IsolateOrigins,site-per-process'
    ]
)
```

**Context Configuration:**
```python
context = await browser.new_context(
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    viewport={'width': 1366, 'height': 768},
    locale='en-US',
    timezone_id='Asia/Kolkata',
    permissions=['geolocation'],
    geolocation={'latitude': 28.6139, 'longitude': 77.2090},
    color_scheme='light',
    extra_http_headers={...}
)
```

**Concurrent Mode (Default):**
```python
tasks = [scrape_tab(context, cat, url, MAX_PAGES) for cat, url in job_urls.items()]
all_pages_data = await asyncio.gather(*tasks)
all_job_data = [item for sublist in all_pages_data for item in sublist]
```

**Sequential Mode (Safer):**
```python
all_job_data = []
for i, (cat, url) in enumerate(job_urls.items()):
    visit_home = (i == 0)
    results = await scrape_tab(context, cat, url, MAX_PAGES, visit_homepage=visit_home)
    all_job_data.extend(results)
    if i < len(job_urls) - 1:
        await asyncio.sleep(random.uniform(15, 25))
```

---

### `run_scraper()`

Wrapper function to run the scraper with error handling and logging.

**Returns:** `None`

**Side Effects:**
- Prints start/completion timestamps
- Runs main() function
- Catches and logs exceptions

**Example:**
```python
run_scraper()
# Output:
# 🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄
# Starting scheduled scrape at January 17, 2026 at 10:30:00 AM
# 🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄🔄
# 
# ... scraping output ...
# 
# ✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅
# Scrape completed at January 17, 2026 at 11:15:00 AM
# ✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅✅
```

**Error Handling:**
```python
try:
    asyncio.run(main())
    print("Scrape completed")
except Exception as e:
    print(f"❌ Error during scheduled scrape: {e}")
```

---

### `if __name__ == "__main__":`

Entry point for scheduled execution.

**Configuration:**
```python
SCRAPE_INTERVAL_HOURS = 3
RUN_IMMEDIATELY = True
```

**Behavior:**
1. Print startup information
2. Schedule periodic execution
3. Optionally run immediately
4. Enter infinite loop checking for scheduled tasks

**Example:**
```python
python naukri_intelligence.py

# Output:
# ================================================================================
# 🤖 JOB SCRAPER SCHEDULER STARTED
# ================================================================================
# ⏰ Scraper will run every 3 hour(s)
# 🕐 Current time: January 17, 2026 at 10:30:00 AM
# ================================================================================
# 
# [Runs scraper immediately if RUN_IMMEDIATELY=True]
# 
# ⏳ Waiting for next scheduled run...
```

**Scheduling:**
```python
schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(run_scraper)

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

**To Stop:**
- Press `Ctrl+C` in terminal

---

## Type Definitions

### Job Dictionary Structure

```python
{
    'Category': str,         # Job category name
    'Page': int,            # Page number where found
    'Title': str,           # Job title
    'Company': str,         # Company name
    'Experience': str,      # Required experience (e.g., "4-7 Yrs")
    'Location': str,        # Job location
    'Salary': str,          # Salary range or "Not disclosed"
    'Time Category': str,   # Categorized time bucket
    'Posted': str,          # Original posting time text
    'Link': str            # Job application URL
}
```

---

## Constants

```python
MAX_PAGES = 50                    # Pages to scrape per category
SCRAPE_INTERVAL_HOURS = 3        # Hours between runs
RUN_IMMEDIATELY = True            # Run on startup

# Browser viewport
VIEWPORT_WIDTH = 1366
VIEWPORT_HEIGHT = 768

# Location (Delhi coordinates)
LATITUDE = 28.6139
LONGITUDE = 77.2090

# Delays (seconds)
MIN_SCROLL_DELAY = 0.5
MAX_SCROLL_DELAY = 2.0
MIN_PAGE_DELAY = 5
MAX_PAGE_DELAY = 10
MIN_CATEGORY_DELAY = 15
MAX_CATEGORY_DELAY = 25
```

---

## Dependencies

```python
# Web Scraping
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup

# Data Processing
import pandas as pd

# Database
import mysql.connector
from mysql.connector import Error

# Email
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Utilities
import asyncio
import random
import os
from datetime import datetime
from dotenv import load_dotenv
import schedule
import time
```

---

## Usage Examples

### Basic Scraping

```python
# Run once
asyncio.run(main())
```

### Scheduled Scraping

```python
# Run every 6 hours
SCRAPE_INTERVAL_HOURS = 6
RUN_IMMEDIATELY = True

schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(run_scraper)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Custom Category

```python
job_urls = {
    'Custom Job': 'https://www.naukri.com/your-search-url'
}

asyncio.run(main())
```

### Testing Database

```python
init_db_mysql()
jobs = get_unsent_jobs()
print(f"Found {len(jobs)} unsent jobs")
```

### Testing Email

```python
test_jobs = get_unsent_jobs()[:5]  # First 5 jobs
success = send_job_emails(test_jobs)
if success:
    mark_jobs_as_sent([job['job_id'] for job in test_jobs])
```

---

## Best Practices

1. **Always use virtual environment**
2. **Keep .env file secure** (never commit)
3. **Monitor database size** regularly
4. **Use reasonable MAX_PAGES** (≤50)
5. **Respect scraping intervals** (≥3 hours)
6. **Check Naukri.com ToS** before deployment
7. **Handle errors gracefully**
8. **Log important events**
9. **Test before production**
10. **Keep dependencies updated**

---

**For more information, see [README.md](README.md) and [SETUP_GUIDE.md](docs/SETUP_GUIDE.md)**