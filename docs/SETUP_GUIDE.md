# 📚 Detailed Setup Guide

This guide provides step-by-step instructions for setting up the Naukri Job Scraper on different operating systems.

## Table of Contents
- [Windows Setup](#windows-setup)
- [macOS Setup](#macos-setup)
- [Linux Setup](#linux-setup)
- [MySQL Installation](#mysql-installation)
- [Python Environment Setup](#python-environment-setup)
- [Gmail Configuration](#gmail-configuration)
- [Testing Your Setup](#testing-your-setup)

---

## Windows Setup

### 1. Install Python

1. Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

### 2. Install MySQL

1. Download [MySQL Community Server](https://dev.mysql.com/downloads/mysql/)
2. Run the installer and choose "Developer Default"
3. Set root password during installation (remember this!)
4. Complete the installation and start MySQL service
5. Verify installation:
   ```cmd
   mysql --version
   ```

### 3. Clone and Setup Project

```cmd
# Open Command Prompt
cd C:\Users\YourUsername\Documents
git clone https://github.com/yourusername/naukri-job-scraper.git
cd naukri-job-scraper

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 4. Configure Environment

1. Copy `.env.example` to `.env`
2. Edit `.env` with Notepad++, VSCode, or any text editor
3. Fill in your MySQL and Gmail credentials

### 5. Setup Database

```cmd
# Login to MySQL
mysql -u root -p

# Run database commands (paste from database_structure.sql)
```

---

## macOS Setup

### 1. Install Homebrew (if not installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python

```bash
brew install python@3.11
python3 --version
pip3 --version
```

### 3. Install MySQL

```bash
brew install mysql
brew services start mysql

# Secure installation
mysql_secure_installation
```

### 4. Clone and Setup Project

```bash
cd ~/Documents
git clone https://github.com/yourusername/naukri-job-scraper.git
cd naukri-job-scraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

### 5. Configure Environment

```bash
cp .env.example .env
nano .env  # or use your preferred editor (vim, code, etc.)
```

### 6. Setup Database

```bash
mysql -u root -p < database_structure.sql
```

---

## Linux Setup (Ubuntu/Debian)

### 1. Update System

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Python

```bash
sudo apt install python3 python3-pip python3-venv -y
python3 --version
```

### 3. Install MySQL

```bash
sudo apt install mysql-server -y
sudo systemctl start mysql
sudo systemctl enable mysql
sudo mysql_secure_installation
```

### 4. Install Git

```bash
sudo apt install git -y
```

### 5. Clone and Setup Project

```bash
cd ~
git clone https://github.com/yourusername/naukri-job-scraper.git
cd naukri-job-scraper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Install Playwright system dependencies
playwright install-deps chromium
```

### 6. Configure Environment

```bash
cp .env.example .env
nano .env
```

### 7. Setup Database

```bash
sudo mysql -u root -p < database_structure.sql
```

---

## MySQL Installation Details

### Windows MySQL Configuration

1. **Open MySQL Workbench** or **Command Line Client**
2. Login with root password
3. Create database:
   ```sql
   CREATE DATABASE naukri_com CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

### macOS/Linux MySQL Configuration

```bash
# Login to MySQL
mysql -u root -p

# Or create user (recommended)
sudo mysql
CREATE USER 'scraper_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON naukri_com.* TO 'scraper_user'@'localhost';
FLUSH PRIVILEGES;
```

### Testing MySQL Connection

```python
# test_db.py
import mysql.connector
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = mysql.connector.connect(
        host=os.getenv('HOST'),
        user=os.getenv('USER'),
        password=os.getenv('PASS'),
        database=os.getenv('DATABASE')
    )
    print("✅ Database connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

---

## Python Environment Setup

### Virtual Environment Best Practices

**Why use virtual environments?**
- Isolates project dependencies
- Prevents version conflicts
- Makes project portable

### Activating Virtual Environment

**Windows:**
```cmd
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Deactivating:**
```bash
deactivate
```

### Installing Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Install individual packages (if needed)
pip install playwright playwright-stealth beautifulsoup4 pandas mysql-connector-python python-dotenv schedule

# Verify installations
pip list
```

### Playwright Browser Setup

```bash
# Install Chromium browser
playwright install chromium

# Install all browsers (optional)
playwright install

# Install system dependencies (Linux only)
playwright install-deps
```

---

## Gmail Configuration

### Step-by-Step Gmail App Password Setup

#### 1. Enable 2-Step Verification

1. Go to [Google Account](https://myaccount.google.com/)
2. Click **Security** in the left menu
3. Under "Signing in to Google", click **2-Step Verification**
4. Follow the prompts to enable it

#### 2. Generate App Password

1. In the same **Security** section, scroll to **App passwords**
2. You may need to sign in again
3. Select app: **Mail**
4. Select device: **Other (Custom name)**
5. Enter: "Naukri Job Scraper"
6. Click **Generate**
7. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)

#### 3. Update .env File

```env
SENDER_EMAIL=your_email@gmail.com
SENDER_PASSWORD=abcdabcdabcdabcd  # 16-char app password (no spaces)
RECIPIENT_EMAIL=recipient@gmail.com
```

### Testing Email Configuration

Create `test_email.py`:

```python
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()

try:
    msg = MIMEText("Test email from Naukri Scraper")
    msg['Subject'] = "Test Email"
    msg['From'] = os.getenv('SENDER_EMAIL')
    msg['To'] = os.getenv('RECIPIENT_EMAIL')
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(os.getenv('SENDER_EMAIL'), os.getenv('SENDER_PASSWORD'))
        server.send_message(msg)
    
    print("✅ Email sent successfully!")
except Exception as e:
    print(f"❌ Email failed: {e}")
```

Run test:
```bash
python test_email.py
```

---

## Testing Your Setup

### Complete Setup Verification

Create `test_setup.py`:

```python
import mysql.connector
import os
from dotenv import load_dotenv
import smtplib

load_dotenv()

def test_database():
    try:
        conn = mysql.connector.connect(
            host=os.getenv('HOST'),
            user=os.getenv('USER'),
            password=os.getenv('PASS'),
            database=os.getenv('DATABASE')
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM job_postings")
        count = cursor.fetchone()[0]
        print(f"✅ Database: Connected (found {count} jobs)")
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database: {e}")
        return False

def test_email():
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(os.getenv('SENDER_EMAIL'), os.getenv('SENDER_PASSWORD'))
        print("✅ Email: Credentials valid")
        return True
    except Exception as e:
        print(f"❌ Email: {e}")
        return False

def test_playwright():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        print("✅ Playwright: Chromium installed")
        return True
    except Exception as e:
        print(f"❌ Playwright: {e}")
        return False

if __name__ == "__main__":
    print("\n" + "="*50)
    print("SETUP VERIFICATION")
    print("="*50 + "\n")
    
    results = {
        "Database": test_database(),
        "Email": test_email(),
        "Playwright": test_playwright()
    }
    
    print("\n" + "="*50)
    if all(results.values()):
        print("✅ ALL TESTS PASSED - Setup Complete!")
    else:
        print("⚠️  Some tests failed - Check errors above")
    print("="*50 + "\n")
```

Run verification:
```bash
python test_setup.py
```

---

## Troubleshooting Setup Issues

### Python Not Found

**Windows:**
- Reinstall Python with "Add to PATH" checked
- Manually add to PATH: `C:\Python311\` and `C:\Python311\Scripts\`

**macOS/Linux:**
```bash
# Check Python location
which python3

# Add to PATH in ~/.bashrc or ~/.zshrc
export PATH="/usr/local/bin/python3:$PATH"
```

### MySQL Connection Refused

```bash
# Check if MySQL is running
# Windows
net start MySQL

# macOS
brew services start mysql

# Linux
sudo systemctl start mysql
sudo systemctl status mysql
```

### Port Already in Use

If MySQL port 3306 is occupied:
```sql
# Change MySQL port in my.cnf or my.ini
[mysqld]
port=3307

# Update .env
HOST=localhost:3307
```

### Playwright Installation Issues

```bash
# Clear Playwright cache
playwright uninstall --all

# Reinstall
playwright install chromium

# Linux: Install dependencies
sudo playwright install-deps
```

---

## Next Steps

After completing setup:

1. ✅ Verify all tests pass
2. 📝 Review and customize job categories in `naukri_intelligence.py`
3. ⚙️ Adjust `MAX_PAGES` and `SCRAPE_INTERVAL_HOURS`
4. 🚀 Run your first scrape: `python naukri_intelligence.py`
5. 📧 Check your email for job alerts!

---

## Getting Help

If you encounter issues:

1. Check [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review error messages carefully
3. Search [GitHub Issues](https://github.com/yourusername/naukri-job-scraper/issues)
4. Open a new issue with:
   - Your OS and Python version
   - Complete error message
   - Steps you've already tried

---

**Good luck with your job search! 🎯**