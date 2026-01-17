# 🔧 Troubleshooting Guide

This guide covers common issues and their solutions when running the Naukri Job Scraper.

## Table of Contents
- [Database Issues](#database-issues)
- [Email Problems](#email-problems)
- [Scraping Issues](#scraping-issues)
- [Playwright Errors](#playwright-errors)
- [Performance Issues](#performance-issues)
- [Error Messages](#common-error-messages)

---

## Database Issues

### Issue: "Can't connect to MySQL server"

**Symptoms:**
```
Error while establishing the connection with MySQL: 2003 (HY000): Can't connect to MySQL server on 'localhost'
```

**Solutions:**

1. **Check if MySQL is running:**
   ```bash
   # Windows
   net start MySQL
   sc query MySQL
   
   # macOS
   brew services list
   brew services start mysql
   
   # Linux
   sudo systemctl status mysql
   sudo systemctl start mysql
   ```

2. **Verify credentials in .env:**
   ```env
   HOST=localhost
   USER=root
   PASS=your_actual_password
   DATABASE=naukri_com
   ```

3. **Test connection manually:**
   ```bash
   mysql -u root -p -h localhost
   ```

4. **Check MySQL port:**
   ```sql
   SHOW VARIABLES LIKE 'port';
   ```
   If not 3306, update HOST in .env: `localhost:3307`

---

### Issue: "Access denied for user"

**Symptoms:**
```
Error: 1045 (28000): Access denied for user 'root'@'localhost' (using password: YES)
```

**Solutions:**

1. **Reset MySQL root password:**
   
   **Windows:**
   ```cmd
   mysqld --skip-grant-tables
   mysql -u root
   
   mysql> ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
   mysql> FLUSH PRIVILEGES;
   ```
   
   **macOS/Linux:**
   ```bash
   sudo mysql
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'new_password';
   FLUSH PRIVILEGES;
   ```

2. **Create dedicated user:**
   ```sql
   CREATE USER 'scraper'@'localhost' IDENTIFIED BY 'secure_password';
   GRANT ALL PRIVILEGES ON naukri_com.* TO 'scraper'@'localhost';
   FLUSH PRIVILEGES;
   ```
   
   Update .env:
   ```env
   USER=scraper
   PASS=secure_password
   ```

---

### Issue: "Database does not exist"

**Symptoms:**
```
Error: 1049 (42000): Unknown database 'naukri_com'
```

**Solutions:**

1. **Create database:**
   ```sql
   CREATE DATABASE naukri_com 
   CHARACTER SET utf8mb4 
   COLLATE utf8mb4_unicode_ci;
   ```

2. **Verify database exists:**
   ```sql
   SHOW DATABASES;
   USE naukri_com;
   SHOW TABLES;
   ```

3. **Run schema file:**
   ```bash
   mysql -u root -p < database_structure.sql
   ```

---

### Issue: "Table doesn't exist"

**Symptoms:**
```
Error: 1146 (42S02): Table 'naukri_com.job_postings' doesn't exist
```

**Solutions:**

```sql
USE naukri_com;
SOURCE database_structure.sql;

-- Or manually create:
CREATE TABLE job_postings (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    salary VARCHAR(100),
    experience VARCHAR(100),
    posting_time VARCHAR(100),
    time_category VARCHAR(50),
    link VARCHAR(500) UNIQUE NOT NULL,
    page_number INT,
    scraped_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    email_sent TINYINT(1) DEFAULT 0,
    INDEX idx_email_sent (email_sent),
    INDEX idx_time_category (time_category)
);
```

---

### Issue: Database growing too large

**Solutions:**

1. **Delete old jobs:**
   ```sql
   -- Delete jobs older than 30 days
   DELETE FROM job_postings 
   WHERE scraped_time < DATE_SUB(NOW(), INTERVAL 30 DAY);
   ```

2. **Archive before deleting:**
   ```sql
   -- Create archive table
   CREATE TABLE job_postings_archive LIKE job_postings;
   
   -- Move old jobs to archive
   INSERT INTO job_postings_archive 
   SELECT * FROM job_postings 
   WHERE scraped_time < DATE_SUB(NOW(), INTERVAL 30 DAY);
   
   -- Delete from main table
   DELETE FROM job_postings 
   WHERE scraped_time < DATE_SUB(NOW(), INTERVAL 30 DAY);
   ```

3. **Check database size:**
   ```sql
   SELECT 
       table_schema AS 'Database',
       ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
   FROM information_schema.tables
   WHERE table_schema = 'naukri_com'
   GROUP BY table_schema;
   ```

---

## Email Problems

### Issue: "SMTPAuthenticationError"

**Symptoms:**
```
SMTPAuthenticationError: (535, b'5.7.8 Username and Password not accepted')
```

**Solutions:**

1. **Use App Password (not regular password):**
   - Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
   - Generate new password
   - Use 16-character code in .env (no spaces)

2. **Enable 2-Step Verification:**
   - Required before creating App Password
   - [Enable here](https://myaccount.google.com/signinoptions/two-step-verification)

3. **Check .env format:**
   ```env
   SENDER_EMAIL=your_email@gmail.com
   SENDER_PASSWORD=abcdabcdabcdabcd  # No spaces!
   ```

---

### Issue: "SMTPServerDisconnected"

**Symptoms:**
```
SMTPServerDisconnected: Connection unexpectedly closed
```

**Solutions:**

1. **Check firewall/antivirus:**
   - Temporarily disable to test
   - Add exception for Python and port 587

2. **Verify SMTP settings:**
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   ```

3. **Test with alternative port:**
   ```env
   SMTP_PORT=465  # Try SSL instead of TLS
   ```
   
   Update code:
   ```python
   # Use SMTP_SSL for port 465
   with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
       server.login(...)
   ```

---

### Issue: Emails not being received

**Solutions:**

1. **Check spam/junk folder**

2. **Verify recipient email:**
   ```env
   RECIPIENT_EMAIL=correct_recipient@gmail.com
   ```

3. **Test email sending:**
   ```python
   # Create test_email.py
   import smtplib
   from email.mime.text import MIMEText
   from dotenv import load_dotenv
   import os
   
   load_dotenv()
   
   msg = MIMEText("Test from scraper")
   msg['Subject'] = "Test"
   msg['From'] = os.getenv('SENDER_EMAIL')
   msg['To'] = os.getenv('RECIPIENT_EMAIL')
   
   with smtplib.SMTP('smtp.gmail.com', 587) as server:
       server.starttls()
       server.login(os.getenv('SENDER_EMAIL'), os.getenv('SENDER_PASSWORD'))
       server.send_message(msg)
       print("Sent!")
   ```

4. **Check Gmail sending limits:**
   - Free Gmail: 500 emails/day
   - Wait 24 hours if limit reached

---

### Issue: HTML email not displaying correctly

**Solutions:**

1. **Some email clients block images/styles:**
   - Gmail web: Should work fine
   - Outlook: May strip some CSS
   - Apple Mail: Generally good support

2. **Use inline styles (already done in code)**

3. **Test in multiple clients:**
   - Gmail web interface
   - Gmail mobile app
   - Outlook
   - Apple Mail

---

## Scraping Issues

### Issue: "No job cards found on page"

**Symptoms:**
```
⚠️ No job cards found on page 1
Found 0 jobs on page 1
```

**Solutions:**

1. **Naukri.com changed HTML structure:**
   - Visit Naukri.com manually
   - Right-click on job card → Inspect
   - Check current class name
   - Update selector in code:
   ```python
   # Current selector
   job_cards = soup.find_all('div', class_='srp-jobtuple-wrapper')
   
   # Try alternatives
   job_cards = soup.find_all('article', class_='job-tuple')
   job_cards = soup.find_all('div', class_='job-card')
   ```

2. **Page not fully loaded:**
   ```python
   # Increase wait time
   await page.wait_for_selector('div.srp-jobtuple-wrapper', timeout=30000)
   await asyncio.sleep(5)  # Add extra delay
   ```

3. **Bot detection triggered:**
   - See [Bot Detection](#issue-bot-detection--captcha) below

---

### Issue: "Next button not found"

**Symptoms:**
```
⚠️ Next button not found - reached last page
```

**Solutions:**

1. **Reached actual last page:**
   - This is normal behavior
   - Scraper will stop automatically

2. **Button selector changed:**
   ```python
   # Update selectors in click_next_button()
   next_selectors = [
       'a.styles_btn-secondary__2AsIP:has-text("Next")',
       'button:has-text("Next")',
       'a[aria-label="Next"]',
       'a.pagination-next',
   ]
   ```

3. **Inspect current pagination:**
   - Visit Naukri.com
   - Navigate to page 2+
   - Inspect Next button
   - Update selector accordingly

---

### Issue: Bot Detection / Captcha

**Symptoms:**
- Captcha appearing in browser
- "Access Denied" messages
- Consistent 0 results
- IP temporarily blocked

**Solutions:**

1. **Switch to sequential mode:**
   ```python
   # In main(), comment concurrent mode
   # Use sequential instead:
   all_job_data = []
   for i, (cat, url) in enumerate(job_urls.items()):
       results = await scrape_tab(context, cat, url, MAX_PAGES)
       all_job_data.extend(results)
       await asyncio.sleep(random.uniform(30, 60))  # Long delay
   ```

2. **Reduce scraping frequency:**
   ```python
   MAX_PAGES = 10  # Instead of 50
   SCRAPE_INTERVAL_HOURS = 6  # Instead of 3
   ```

3. **Increase delays:**
   ```python
   # In human_like_behavior()
   await asyncio.sleep(random.uniform(3, 6))  # Instead of 1-2
   
   # Before clicking Next
   await asyncio.sleep(random.uniform(10, 20))  # Instead of 5-10
   ```

4. **Use residential proxy (advanced):**
   ```python
   context = await browser.new_context(
       proxy={
           "server": "http://proxy-server:port",
           "username": "user",
           "password": "pass"
       }
   )
   ```

5. **Rotate user agents:**
   ```python
   user_agents = [
       "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
       "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
       "Mozilla/5.0 (X11; Linux x86_64)..."
   ]
   
   context = await browser.new_context(
       user_agent=random.choice(user_agents)
   )
   ```

6. **Wait before retrying:**
   - If blocked, wait 24 hours
   - Don't retry immediately
   - Consider using mobile data or VPN

---

### Issue: Duplicate jobs in database

**Solutions:**

1. **Check UNIQUE constraint:**
   ```sql
   SHOW CREATE TABLE job_postings;
   -- Should show: UNIQUE KEY on 'link' column
   ```

2. **Add constraint if missing:**
   ```sql
   ALTER TABLE job_postings 
   ADD UNIQUE KEY unique_link (link);
   ```

3. **Remove existing duplicates:**
   ```sql
   DELETE j1 FROM job_postings j1
   INNER JOIN job_postings j2 
   WHERE j1.job_id > j2.job_id 
   AND j1.link = j2.link;
   ```

---

## Playwright Errors

### Issue: "Executable doesn't exist"

**Symptoms:**
```
playwright._impl._api_types.Error: Executable doesn't exist at /path/to/chromium
```

**Solutions:**

1. **Install Chromium:**
   ```bash
   playwright install chromium
   ```

2. **Install all browsers:**
   ```bash
   playwright install
   ```

3. **Check installation:**
   ```bash
   playwright --version
   ```

4. **Reinstall if corrupted:**
   ```bash
   playwright uninstall --all
   playwright install chromium
   ```

---

### Issue: Playwright browser crashes

**Solutions:**

1. **Install system dependencies (Linux):**
   ```bash
   sudo playwright install-deps chromium
   ```

2. **Increase memory:**
   ```python
   browser = await p.chromium.launch(
       args=['--disable-dev-shm-usage']  # Use /tmp instead of /dev/shm
   )
   ```

3. **Use headless mode:**
   ```python
   browser = await p.chromium.launch(headless=True)
   ```

4. **Check system resources:**
   ```bash
   # Linux
   free -h
   df -h
   
   # Close other applications
   ```

---

### Issue: Timeout errors

**Symptoms:**
```
TimeoutError: Timeout 30000ms exceeded
```

**Solutions:**

1. **Increase timeout:**
   ```python
   await page.goto(url, wait_until="networkidle", timeout=60000)
   await page.wait_for_selector('div.srp-jobtuple-wrapper', timeout=30000)
   ```

2. **Use different wait strategy:**
   ```python
   await page.goto(url, wait_until="domcontentloaded")  # Faster
   # Instead of wait_until="networkidle"
   ```

3. **Check internet connection:**
   ```bash
   ping google.com
   ```

---

## Performance Issues

### Issue: Scraper running very slow

**Solutions:**

1. **Use concurrent mode:**
   ```python
   # In main()
   tasks = [scrape_tab(context, cat, url, MAX_PAGES) for cat, url in job_urls.items()]
   all_pages_data = await asyncio.gather(*tasks)
   ```

2. **Reduce human behavior simulation:**
   ```python
   # In human_like_behavior()
   for _ in range(random.randint(1, 2)):  # Instead of 2-4
       await page.mouse.wheel(0, random.randint(100, 300))
       await asyncio.sleep(random.uniform(0.2, 0.5))  # Shorter delays
   ```

3. **Use headless mode:**
   ```python
   browser = await p.chromium.launch(headless=True)
   ```

4. **Limit pages:**
   ```python
   MAX_PAGES = 20  # Instead of 50
   ```

---

### Issue: High memory usage

**Solutions:**

1. **Close pages after scraping:**
   ```python
   async def scrape_tab(...):
       try:
           # ... scraping code ...
       finally:
           await page.close()  # Already implemented
   ```

2. **Process in batches:**
   ```python
   # Don't scrape all categories at once
   # Process 2-3 at a time
   ```

3. **Clear pandas display options:**
   ```python
   # Remove or limit
   # pd.set_option('display.max_rows', None)
   pd.set_option('display.max_rows', 100)
   ```

---

## Common Error Messages

### "ModuleNotFoundError: No module named 'playwright'"

```bash
pip install playwright
playwright install chromium
```

### "ModuleNotFoundError: No module named 'dotenv'"

```bash
pip install python-dotenv
```

### "NameError: name 'asyncio' is not defined"

Already imported in code. If error persists:
```python
import asyncio
```

### "AttributeError: 'NoneType' object has no attribute 'text'"

Job element not found. Update selectors or add null checks:
```python
title_tag = job.find('a', class_='title')
title = title_tag.text.strip() if title_tag else 'N/A'
```

### ".env file not found"

```bash
cp .env.example .env
# Then edit .env with your credentials
```

---

## Debug Mode

Enable verbose logging:

```python
# Add at top of naukri_intelligence.py
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

Save page HTML for inspection:

```python
# After scraping page
html_content = await page.content()
with open(f'page_{page_num}.html', 'w', encoding='utf-8') as f:
    f.write(html_content)
```

Take screenshots:

```python
# When errors occur
await page.screenshot(path=f'error_{datetime.now()}.png')
```

---

## Getting More Help

If issues persist:

1. **Enable debug mode** (see above)
2. **Save error logs** to file
3. **Take screenshots** of browser state
4. **Check [GitHub Issues](https://github.com/yourusername/naukri-job-scraper/issues)**
5. **Open new issue** with:
   - Full error traceback
   - OS and Python version
   - Steps to reproduce
   - Screenshots/logs

---

**Still stuck? Open an issue on GitHub!** 🐛