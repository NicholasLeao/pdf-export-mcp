#!/usr/bin/env python3
"""Test script for PDF export functionality - bypassing MCP."""

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from pyppeteer import launch
import io

# Export directory configuration
EXPORT_DIR = "/tmp/protex-intelligence-file-exports"

# Hardcoded test data
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Report</title>
</head>
<body>
    <h1>Company Sales Report</h1>
    <h2>Q4 2024 Performance</h2>
    
    <div class="summary">
        <h3>Executive Summary</h3>
        <p>This quarter has shown exceptional growth across all departments. Our sales team exceeded targets by 15%, while customer satisfaction remained at an all-time high of 94%.</p>
    </div>
    
    <div class="metrics">
        <h3>Key Metrics</h3>
        <table>
            <thead>
                <tr>
                    <th>Department</th>
                    <th>Target</th>
                    <th>Actual</th>
                    <th>Growth</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Sales</td>
                    <td>$2.5M</td>
                    <td>$2.875M</td>
                    <td>+15%</td>
                </tr>
                <tr>
                    <td>Marketing</td>
                    <td>500 leads</td>
                    <td>625 leads</td>
                    <td>+25%</td>
                </tr>
                <tr>
                    <td>Support</td>
                    <td>90% satisfaction</td>
                    <td>94% satisfaction</td>
                    <td>+4%</td>
                </tr>
            </tbody>
        </table>
    </div>
    
    <div class="conclusion">
        <h3>Next Steps</h3>
        <ul>
            <li>Expand the sales team by 20%</li>
            <li>Invest in new marketing automation tools</li>
            <li>Launch customer loyalty program</li>
            <li>Implement AI-powered support chatbot</li>
        </ul>
    </div>
</body>
</html>
"""

TEST_CSS = """
body {
    font-family: 'Arial', sans-serif;
    line-height: 1.6;
    color: #333;
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
}

h1 {
    color: #2c3e50;
    border-bottom: 3px solid #3498db;
    padding-bottom: 10px;
}

h2 {
    color: #34495e;
    margin-top: 30px;
}

h3 {
    color: #7f8c8d;
    margin-top: 25px;
    margin-bottom: 15px;
}

.summary, .metrics, .conclusion {
    margin: 25px 0;
    padding: 20px;
    background-color: #f8f9fa;
    border-left: 4px solid #3498db;
    border-radius: 5px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 15px;
}

th, td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #3498db;
    color: white;
    font-weight: bold;
}

tr:nth-child(even) {
    background-color: #f2f2f2;
}

ul {
    padding-left: 20px;
}

li {
    margin-bottom: 8px;
}
"""

TEST_ARGUMENTS = {
    "html": TEST_HTML,
    "css": TEST_CSS,
    "filename": "sales_report_q4_2024",
    "description": "Quarterly sales report with performance metrics",
    "options": {
        "format": "A4",
        "orientation": "portrait",
        "margin": {
            "top": "25mm",
            "right": "25mm",
            "bottom": "25mm",
            "left": "25mm"
        },
        "printBackground": True
    }
}


async def generate_pdf(
    html: str,
    css: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None
) -> bytes:
    """Generate PDF from HTML using Pyppeteer."""
    if not html:
        raise ValueError("HTML content cannot be empty")
    
    # Set default options
    options = options or {}
    browser = None
    
    try:
        # Combine HTML and CSS if CSS is provided
        full_html = html
        if css:
            if '<head>' in html:
                full_html = html.replace('<head>', f'<head><style>{css}</style>')
            elif '<html>' in html:
                full_html = html.replace('<html>', f'<html><head><style>{css}</style></head>')
            else:
                full_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>{css}</style>
</head>
<body>
{html}
</body>
</html>"""
        
        # Ensure full_html has basic HTML structure
        if not full_html.startswith('<!DOCTYPE') and '<html' not in full_html:
            full_html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
</head>
<body>
{full_html}
</body>
</html>"""
        
        # Launch Pyppeteer
        print("🚀 Launching Pyppeteer browser...")
        browser = await launch({
            'headless': True,
            'args': ['--no-sandbox', '--disable-setuid-sandbox']
        })
        
        page = await browser.newPage()
        
        # Set content
        await page.setContent(full_html)
        await page.waitFor(1000)  # Wait 1 second for content to load
        
        # Prepare PDF options
        pdf_options = {
            'format': options.get('format', 'A4'),
            'landscape': options.get('orientation', 'portrait') == 'landscape',
            'printBackground': options.get('printBackground', True),
            'margin': options.get('margin', {
                'top': '20mm',
                'right': '20mm', 
                'bottom': '20mm',
                'left': '20mm'
            })
        }
        
        # Add header/footer if specified
        if options.get('displayHeaderFooter'):
            pdf_options['displayHeaderFooter'] = True
            pdf_options['headerTemplate'] = options.get('headerTemplate', '')
            pdf_options['footerTemplate'] = options.get('footerTemplate', '')
        
        # Generate PDF
        print("📄 Generating PDF...")
        pdf_bytes = await page.pdf(pdf_options)
        
        # Close browser
        await browser.close()
        
        return pdf_bytes
        
    except Exception as error:
        # Ensure browser is closed on error
        if browser:
            try:
                await browser.close()
            except Exception as close_error:
                print(f"Error closing browser: {close_error}")
        raise error


def get_file_size_string(content: bytes) -> str:
    """Calculate file size string from bytes content."""
    bytes_size = len(content)
    kb = bytes_size / 1024
    
    if kb < 1024:
        return f"{kb:.0f} KB" if kb >= 1 else "1 KB"
    else:
        return f"{kb / 1024:.2f} MB"


async def ensure_export_directory() -> None:
    """Ensure export directory exists, create if it doesn't."""
    export_path = Path(EXPORT_DIR)
    
    if export_path.exists():
        print(f"✓ Export directory exists: {EXPORT_DIR}")
    else:
        try:
            export_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created export directory: {EXPORT_DIR}")
        except Exception as e:
            print(f"✗ Failed to create export directory: {e}")
            raise


async def write_pdf_to_file(pdf_content: bytes, filename: str) -> str:
    """Write PDF content to file system."""
    await ensure_export_directory()
    
    filepath = Path(EXPORT_DIR) / filename
    
    try:
        filepath.write_bytes(pdf_content)
        print(f"✓ File written: {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"✗ Failed to write file: {e}")
        raise


async def test_pdf_export():
    """Test the PDF export functionality."""
    print("🧪 Testing PDF Export Logic")
    print("=" * 50)
    
    try:
        # Extract arguments
        html = TEST_ARGUMENTS.get("html")
        css = TEST_ARGUMENTS.get("css")
        filename = TEST_ARGUMENTS.get("filename", "output")
        description = TEST_ARGUMENTS.get("description")
        options = TEST_ARGUMENTS.get("options", {})
        
        print(f"📄 HTML Content: {len(html)} characters")
        print(f"🎨 CSS Content: {len(css) if css else 0} characters")
        print(f"📄 Filename: {filename}")
        print(f"📝 Description: {description}")
        print(f"⚙️  Options: {options}")
        print()
        
        # Validate input
        if not html or not isinstance(html, str):
            raise ValueError("HTML content must be provided as a string")
        
        if html.strip() == "":
            raise ValueError("HTML content cannot be empty")
        
        # Generate PDF
        print("🔄 Converting HTML to PDF format...")
        pdf_content = await generate_pdf(html, css, options)
        
        # Generate UUID and filename
        file_uuid = str(uuid.uuid4())
        sanitized_filename = "".join(c if c.isalnum() or c in "_-" else "_" for c in filename)
        full_filename = f"{sanitized_filename}_{file_uuid}.pdf"
        file_size = get_file_size_string(pdf_content)
        
        # Write PDF to file system
        print("💾 Writing file to disk...")
        filepath = await write_pdf_to_file(pdf_content, full_filename)
        
        print()
        print("✅ PDF Export Successful!")
        print(f"📁 Generated file: {full_filename}")
        print(f"📏 File size: {file_size}")
        print(f"💾 Saved to: {filepath}")
        
        # Create result object (same as MCP server would return)
        result = {
            "path": full_filename,
            "filetype": "application/pdf",
            "filename": full_filename,
            "filesize": file_size,
        }
        
        print()
        print("📤 MCP Server Response:")
        print(json.dumps(result, indent=2))
        
    except Exception as error:
        print(f"❌ Error during PDF export: {error}")
        
        error_result = {
            "success": False,
            "error": str(error),
        }
        
        print()
        print("📤 MCP Server Error Response:")
        print(json.dumps(error_result, indent=2))


if __name__ == "__main__":
    asyncio.run(test_pdf_export())