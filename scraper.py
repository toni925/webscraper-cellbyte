#!/usr/bin/env python3
"""
Canadian Drug Agency (CDA) Reimbursement Data Scraper
Web Scraping + PDF Processing + OpenAI Extraction

"""

import os
import json
import pandas as pd
import requests
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

# Third-party imports
try:
    import PyPDF2
    from openai import OpenAI
    import undetected_chromedriver as uc
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please install: pip install PyPDF2 openai pandas requests selenium undetected-chromedriver")
    exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CDAReimbursementScraper:
    """CDA Reimbursement Data Scraper with PDF Processing"""

    def __init__(self):
        self.load_api_key()
        self.setup_openai()
        self.output_csv = "cda_reimbursement_data.csv"
        self.pdf_cache_dir = "pdf_cache"
        self.changelog_file = "changelog.txt"
        self.setup_directories()

        # CDA website URLs
        self.base_url = "https://www.cda-amc.ca"
        self.find_reports_url = "https://www.cda-amc.ca/find-reports"

        # WebDriver will be initialized when needed
        self.driver = None

    def load_api_key(self):
        """Load OpenAI API key from env.dev file"""
        api_key = None

        if os.path.exists('env.dev'):
            with open('env.dev', 'r') as f:
                for line in f:
                    if line.startswith('OPEN_AI_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        break

        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')

        if not api_key:
            raise ValueError("OpenAI API key not found. Please add it to env.dev file")

        self.api_key = api_key

    def setup_openai(self):
        """Initialize OpenAI client"""
        self.openai_client = OpenAI(api_key=self.api_key)

    def setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.pdf_cache_dir, exist_ok=True)

    def setup_browser(self):
        """Setup undetected-chromedriver"""
        if self.driver:
            return

        try:
            # MINIMAL configuration that works
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Create simple Chrome instance - EXACT WORKING CONFIG
            self.driver = uc.Chrome(
                options=options,
                version_main=140
            )

            logger.info("ChromeDriver initialized successfully!")

        except Exception as e:
            logger.error(f"Failed to setup ChromeDriver: {e}")
            raise

    def cleanup_webdriver(self):
        """Cleanup WebDriver resources"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("WebDriver closed")

    def download_pdf(self, url: str, filename: str) -> Optional[str]:
        """Download PDF document using WebDriver navigation (bypass 403 errors)"""
        filepath = os.path.join(self.pdf_cache_dir, filename)

        if os.path.exists(filepath):
            logger.info(f"PDF already cached: {filename}")
            return filepath

        try:
            logger.info(f"Downloading PDF: {filename}")
            logger.info(f"URL: {url}")
            
            # Try WebDriver approach first - navigate directly to PDF
            if self.driver:
                try:
                    # Navigate to PDF URL using WebDriver (maintains session)
                    self.driver.get(url)
                    time.sleep(3)  # Wait for PDF to load
                    
                    # Check if we got the PDF or an error page
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source[:500]
                    
                    if 'pdf' in current_url.lower() and 'error' not in page_source.lower():
                        # Use requests with WebDriver's cookies to download
                        cookies = {}
                        selenium_cookies = self.driver.get_cookies()
                        for cookie in selenium_cookies:
                            cookies[cookie['name']] = cookie['value']
                        
                        headers = {
                            'User-Agent': self.driver.execute_script("return navigator.userAgent;"),
                            'Accept': 'application/pdf,application/octet-stream,*/*',
                            'Referer': 'https://www.cda-amc.ca/find-reports',
                        }
                        
                        session = requests.Session()
                        session.headers.update(headers)
                        
                        # Add all cookies to session
                        for name, value in cookies.items():
                            session.cookies.set(name, value, domain='cda-amc.ca')
                        
                        # Download using the session that worked for WebDriver
                        response = session.get(current_url, timeout=30, stream=True)
                        
                        logger.info(f"WebDriver download - Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'Unknown')}")
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', '').lower()
                            if 'pdf' in content_type or 'octet-stream' in content_type:
                                with open(filepath, 'wb') as f:
                                    for chunk in response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                
                                if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                                    logger.info(f"Successfully downloaded via WebDriver: {filename} ({os.path.getsize(filepath)} bytes)")
                                    return filepath
                                else:
                                    logger.error(f"Downloaded file too small: {filename}")
                            else:
                                logger.error(f"WebDriver method - Not a PDF: {content_type}")
                        else:
                            logger.error(f"WebDriver download failed with status {response.status_code}")
                    else:
                        logger.error(f"WebDriver navigation failed - Current URL: {current_url}")
                        logger.debug(f"Page source preview: {page_source}")
                        
                except Exception as e:
                    logger.warning(f"WebDriver download failed: {e}")
            
            # Fallback: Try direct requests approach with enhanced headers
            try:
                logger.info("Trying fallback direct download...")
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'same-origin',
                    'Referer': 'https://www.cda-amc.ca/find-reports',
                    'Cache-Control': 'max-age=0'
                }
                
                response = requests.get(url, headers=headers, timeout=30, stream=True, allow_redirects=True)
                
                logger.info(f"Direct download - Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'Unknown')}")
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'pdf' in content_type or 'octet-stream' in content_type:
                        with open(filepath, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                        
                        if os.path.exists(filepath) and os.path.getsize(filepath) > 1000:
                            logger.info(f"Successfully downloaded via direct method: {filename} ({os.path.getsize(filepath)} bytes)")
                            return filepath
                    else:
                        logger.error(f"Direct method - Not a PDF: {content_type}")
                else:
                    logger.error(f"Direct download failed with status {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Direct download failed: {e}")
                
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")
            
        return None

    def extract_text_from_pdf(self, filepath: str) -> str:
        """Extract text from PDF"""
        try:
            with open(filepath, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except:
                        logger.error(f"Could not decrypt PDF: {filepath}")
                        return ""
                
                text = ""
                for page in reader.pages:
                    try:
                        text += page.extract_text() + "\n"
                    except:
                        continue
                
                if text.strip():
                    logger.info(f"Extracted {len(text)} characters from {filepath}")
                    return text.strip()
                    
        except Exception as e:
            logger.error(f"Error reading PDF {filepath}: {e}")
            
        return ""

    def extract_data_with_openai(self, text: str, pdf_filename: str) -> Dict:
        """Extract structured data from PDF text using OpenAI"""
        if not text.strip():
            return {}

        prompt = """
        Extract the following information from this Canadian Drug Agency "Recommendation and Reasons" document.
        Focus on accuracy and extract information exactly as requested.
        Return as JSON:

        {
            "brand_name": "Brand/trade name of the drug",
            "generic_name": "Generic/chemical name of the drug", 
            "therapeutic_area": "Medical/therapeutic area or disease category",
            "indication": "Specific medical indication/condition being treated",
            "sponsor": "Pharmaceutical company/sponsor name",
            "submission_date": "Date when submission was made (YYYY-MM-DD if possible)",
            "recommendation_date": "Date of recommendation (YYYY-MM-DD if possible)",
            "recommendation_type": "Type of recommendation (e.g., 'Reimburse', 'Do not reimburse', etc.)",
            "rationale": "Extract specifically from Summary section: 'Which Patients Are Eligible for Coverage?' and 'What Are the Conditions for Reimbursement?' - combine both sections"
        }

        If any field is not found, use "Not specified".
        For rationale, look specifically in the Summary section for patient eligibility and reimbursement conditions.

        Document text:
        """ + text[:4000]

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Extract data from pharmaceutical documents. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            if result_text.startswith('```json'):
                result_text = result_text[7:]
            if result_text.endswith('```'):
                result_text = result_text[:-3]
            
            result = json.loads(result_text)
            
            # Add metadata fields required by specification
            result['document_link'] = pdf_filename  # Will be updated with actual URL
            result['extraction_date'] = datetime.now().isoformat()
            
            logger.info(f"Successfully extracted data from {pdf_filename}")
            return result
            
        except Exception as e:
            logger.error(f"OpenAI extraction failed for {pdf_filename}: {e}")
            return {}

    def scrape_reports(self) -> List[Dict]:
        """Scrape CDA website"""
        logger.info("Starting simple CDA scraping...")
        reports = []
        
        try:
            self.setup_simple_browser()
            
            # Go directly to the page
            logger.info(f"Navigating to: {self.find_reports_url}")
            self.driver.get(self.find_reports_url)
            
            # Simple wait
            time.sleep(10)
            
            # Check page title
            title = self.driver.title
            logger.info(f"Page title: {title}")
            
            # Find all links
            links = self.driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Found {len(links)} links")
            
            # Enhanced search for Reimbursement Review Reports
            # First, try to find the filter/toggle for "Reimbursement Review Report"
            try:
                # Look for filter elements or toggles
                filter_elements = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
                for elem in filter_elements:
                    try:
                        # Check if this is the Reimbursement Review Report filter
                        parent = elem.find_element(By.XPATH, "./..")
                        if "reimbursement review report" in parent.text.lower():
                            if not elem.is_selected():
                                elem.click()
                                time.sleep(2)
                                logger.info("Activated Reimbursement Review Report filter")
                    except:
                        continue
            except:
                logger.info("Could not find filter toggles, proceeding with manual filtering")
            
            # Wait for any dynamic content to load after filtering
            time.sleep(3)
            
            # Enhanced link detection for PDF documents
            pdf_links_found = 0
            for i, link in enumerate(links):  # Check all links now
                try:
                    href = link.get_attribute("href")
                    text = link.text.strip()
                    
                    if i < 10:  # Debug first 10 links
                        logger.info(f"Link {i+1}: '{text}' -> {href}")
                    
                    if href and text:
                        # Focus specifically on PDF links or "Opens in new tab" indicators
                        is_pdf_link = href.endswith('.pdf')
                        is_potential_pdf = ('opens in new tab' in text.lower() and 
                                          ('recommendation' in text.lower() or 'reason' in text.lower()))
                        
                        # Also capture any "Recommendation and Reasons" type links
                        is_recommendation_link = ('recommendation' in text.lower() and 
                                                ('reason' in text.lower() or 'final' in text.lower()))
                        
                        if is_pdf_link or is_potential_pdf or is_recommendation_link:
                            # Get surrounding context for filtering
                            context = ""
                            try:
                                parent = link.find_element(By.XPATH, "./../../..")
                                context = parent.text.lower()
                            except:
                                context = text.lower()
                            
                            # Filter for Reimbursement Review Reports
                            is_reimbursement = ('reimbursement' in context or 
                                              'recommendation' in text.lower() or
                                              'final' in text.lower())
                            
                            if is_reimbursement:
                                # For "Opens in new tab" links, try to resolve actual URL
                                actual_url = href
                                
                                if 'opens in new tab' in text.lower() and not href.endswith('.pdf'):
                                    try:
                                        # Store current window
                                        main_window = self.driver.current_window_handle
                                        
                                        # Click the link to open in new tab
                                        self.driver.execute_script("arguments[0].click();", link)
                                        time.sleep(2)
                                        
                                        # Switch to new window/tab
                                        all_windows = self.driver.window_handles
                                        if len(all_windows) > 1:
                                            for window in all_windows:
                                                if window != main_window:
                                                    self.driver.switch_to.window(window)
                                                    time.sleep(1)
                                                    
                                                    # Get the actual URL (might be PDF)
                                                    current_url = self.driver.current_url
                                                    if current_url.endswith('.pdf') or 'pdf' in current_url.lower():
                                                        actual_url = current_url
                                                        pdf_links_found += 1
                                                    
                                                    # Close tab and return to main
                                                    self.driver.close()
                                                    self.driver.switch_to.window(main_window)
                                                    break
                                    except Exception as e:
                                        logger.warning(f"Could not resolve URL for: {text[:50]}")
                                        # Keep original URL as fallback
                                
                                # Add the report regardless of URL type - we'll handle it in download
                                if actual_url:
                                    reports.append({
                                        'title': text.replace('Opens in new tab', '').strip(),
                                        'url': actual_url,
                                        'category': 'Reimbursement Review Report',
                                        'context': context[:200]
                                    })
                                    logger.info(f"Found Reimbursement Review Report: {text}")
                                    if actual_url.endswith('.pdf'):
                                        pdf_links_found += 1
                except:
                    continue
            
            logger.info(f"Found {pdf_links_found} direct PDF links out of {len(reports)} total reports")
            
        except Exception as e:
            logger.error(f"Scraping error: {e}")
        
        logger.info(f"Found {len(reports)} reports")
        return reports

    def process_reports(self, reports: List[Dict]) -> List[Dict]:
        """Process reports and extract data"""
        logger.info(f"Processing {len(reports)} reports...")
        extracted_data = []
        
        for i, report in enumerate(reports, 1):
            logger.info(f"Processing {i}/{len(reports)}: {report['title']}")
            
            # Generate filename
            safe_title = "".join(c for c in report['title'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
            filename = f"{safe_title[:50]}.pdf"
            
            # Download and process PDF
            pdf_path = self.download_pdf(report['url'], filename)
            if pdf_path:
                text = self.extract_text_from_pdf(pdf_path)
                if text:
                    data = self.extract_data_with_openai(text, filename)
                    if data:
                        # Add required metadata from report
                        data['document_link'] = report['url']
                        data['report_title'] = report['title']
                        data['category'] = report['category']
                        extracted_data.append(data)
                    else:
                        logger.warning(f"No structured data extracted from {filename}")
                else:
                    logger.warning(f"No text extracted from {filename}")
            else:
                logger.error(f"Failed to download: {report['title']}")
        
        return extracted_data

    def save_to_csv(self, data: List[Dict]):
        """Save data to CSV with incremental updates and change tracking"""
        if not data:
            logger.warning("No data to save")
            return
            
        new_df = pd.DataFrame(data)
        changes = []
        
        # Check if CSV exists for incremental updates
        if os.path.exists(self.output_csv):
            try:
                existing_df = pd.read_csv(self.output_csv)
                
                # Identify new and updated records
                # Use document_link as unique identifier
                for _, new_row in new_df.iterrows():
                    doc_link = new_row.get('document_link', '')
                    
                    # Check if this document already exists
                    existing_mask = existing_df['document_link'] == doc_link
                    
                    if existing_mask.any():
                        # Document exists, check for changes
                        existing_row = existing_df[existing_mask].iloc[0]
                        
                        # Compare key fields for changes
                        key_fields = ['brand_name', 'recommendation_type', 'rationale']
                        has_changes = False
                        
                        for field in key_fields:
                            if str(new_row.get(field, '')) != str(existing_row.get(field, '')):
                                has_changes = True
                                changes.append(f"Updated {field} for {new_row.get('brand_name', 'Unknown')}")
                        
                        if has_changes:
                            # Update existing record
                            existing_df.loc[existing_mask] = new_row
                            logger.info(f"Updated record for {new_row.get('brand_name', 'Unknown')}")
                    else:
                        # New document
                        existing_df = pd.concat([existing_df, new_row.to_frame().T], ignore_index=True)
                        changes.append(f"Added new record: {new_row.get('brand_name', 'Unknown')}")
                        logger.info(f"Added new record for {new_row.get('brand_name', 'Unknown')}")
                
                final_df = existing_df
                
            except Exception as e:
                logger.warning(f"Error reading existing CSV: {e}. Creating new file.")
                final_df = new_df
                changes = [f"Created new CSV with {len(new_df)} records"]
        else:
            final_df = new_df
            changes = [f"Created new CSV with {len(new_df)} records"]
        
        # Save updated CSV
        final_df.to_csv(self.output_csv, index=False)
        logger.info(f"Saved {len(final_df)} total records to {self.output_csv}")
        
        # Log changes
        if changes:
            self.log_changes(changes)
    
    def log_changes(self, changes: List[str]):
        """Log changes to changelog file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.changelog_file, 'a', encoding='utf-8') as f:
                f.write(f"\n=== {timestamp} ===\n")
                for change in changes:
                    f.write(f"- {change}\n")
            logger.info(f"Logged {len(changes)} changes to {self.changelog_file}")
        except Exception as e:
            logger.error(f"Failed to write changelog: {e}")

    def run(self):
        """Main execution"""
        logger.info("=== Simple CDA Scraper Starting ===")
        
        try:
            reports = self.scrape_reports()
            if reports:
                data = self.process_reports(reports)
                self.save_to_csv(data)
            else:
                logger.warning("No reports found")
        except Exception as e:
            logger.error(f"Script error: {e}")
        finally:
            self.cleanup_webdriver()


def main():
    try:
        scraper = CDAReimbursementScraper()
        scraper.run()
    except Exception as e:
        logger.error(f"Failed: {e}")


if __name__ == "__main__":
    main()