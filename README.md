# CDA Reimbursement Data Scraper

A production-ready Python web scraper that extracts Canadian Drug Agency (CDA) reimbursement review reports, processes PDF documents, and generates structured CSV data. **Successfully bypasses Cloudflare protection** using `undetected-chromedriver` and focuses specifically on **Reimbursement Review Report** category.

## 🎯 Requirements Compliance

### ✅ **Exact Data Extraction Fields**
- **Brand Name** - Extracted from PDF documents
- **Generic Name** - Chemical/generic drug name
- **Therapeutic Area** - Medical/disease category
- **Indication** - Specific medical condition (from documents only)
- **Sponsor** - Pharmaceutical company (from documents)
- **Submission Date** - When submission was made
- **Recommendation Date** - Date of recommendation
- **Recommendation Type** - Reimburse/Do not reimburse decision
- **Rationale** - From Summary section: "Which Patients Are Eligible for Coverage?" and "What Are the Conditions for Reimbursement?"
- **Document Link** - URL to source document

### ✅ **Technical Features**
- **Real Web Scraping** with Cloudflare bypass using `ultrafunkamsterdam/undetected-chromedriver`
- **Category Filtering** - Only "Reimbursement Review Report" category
- **Document Focus** - Targets "Recommendation and Reasons" PDFs specifically
- **OpenAI Integration** - GPT-4 for intelligent data extraction
- **Incremental Updates** - Detects new entries and updates existing ones
- **Change Tracking** - Logs all changes in `changelog.txt`
- **Error Handling** - Robust logging and error recovery
- **CSV Template Compliance** - Exact column order as specified
- **Duplicate prevention**: Checks Brand Name + Generic Name combinations  
- **Data persistence**: Preserves existing entries across runs
- **Error handling**: Robust logging for debugging issues

## Output CSV Structure

The script generates `cda_reimbursement_data.csv` with these columns:

| Column | Description | Source |
|--------|-------------|---------|
| Brand Name | Trade/brand name of drug | PDF content |
| Generic Name | Generic/chemical name | PDF content |
| Therapeutic Area | Medical area (e.g., Oncology) | PDF content |
| Indication | Medical condition treated | PDF content |
| Sponsor | Pharmaceutical company | PDF content |
| Submission Date | Date submitted (YYYY-MM-DD) | PDF content |
| Recommendation Date | Date of recommendation | PDF content |
| Recommendation Type | Recommendation category | PDF content |
| Rationale | Summary from eligibility/conditions sections | PDF content |
| Document Link | URL to source PDF | Discovered URL |

## Approach & Architecture

### Separation of Concerns
- **`CDAReimbursementScraper`**: Main orchestration class
- **Web scraping methods**: Handle site navigation and protection bypass
- **PDF processing methods**: Download and extract content
- **Data extraction methods**: OpenAI integration for structured parsing
- **Data management methods**: CSV operations and incremental updates

### Error Handling & Reliability
- **Comprehensive logging** at INFO level for debugging
- **Multi-strategy PDF downloads** for blocked content
- **Graceful degradation** when documents are unavailable
- **Honest failure reporting** (no fake/sample data generation)

### Efficiency & Cost Optimization
- **Intelligent PDF filtering** to reduce unnecessary processing
- **Text truncation** to stay within OpenAI token limits
- **Caching mechanisms** to avoid re-downloading existing PDFs
- **Rate limiting** with human-like delays

### Maintainability & Scalability
- **Modular design** with clear method responsibilities
- **Configurable parameters** (API keys, output paths, limits)
- **Extensible filtering** for different document categories
- **Version control ready** with proper .gitignore patterns

## Configuration

Key configurable elements in the script:
- `MAX_PDFS_TO_PROCESS = 5`: Limit processing for testing
- `pdf_cache_dir = "pdf_cache"`: PDF storage directory  
- `output_csv = "cda_reimbursement_data.csv"`: Output filename
- OpenAI model selection and parameters

## LLM Integration

### Prompt Design
- **Structured extraction prompts** with clear field specifications
- **JSON format requirements** for consistent parsing
- **Context-aware instructions** for pharmaceutical documents
- **Error handling** for malformed responses

### Efficiency Measures
- **Content truncation** to 4000 characters max
- **Single-shot extraction** rather than iterative refinement
- **Focused field extraction** only for required columns
- **Response validation** and graceful error handling

## Technical Implementation

### Anti-Detection Measures
- **Undetected-chromedriver** for stealth browsing
- **Human-like navigation patterns** with realistic delays
- **Randomized browser fingerprints** and window sizes
- **Session-based PDF downloads** using authenticated browser

### PDF Handling
- **PyPDF2** for standard PDF text extraction
- **PyCryptodome** for encrypted document support
- **Multiple download strategies** for different blocking scenarios
- **Content validation** before processing

This solution demonstrates real-world web scraping challenges and provides a production-ready approach to automated data extraction from government pharmaceutical databases.
- **Duplicate Detection**: Prevents duplicate entries based on Brand Name + Generic Name
- **Smart Extraction**: Generates all available entries from CDA reports
- **Error Handling**: Graceful failure if OpenAI API issues occur