#!/usr/bin/env python3
"""PDF Export MCP Server - Python implementation."""

import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pyppeteer import launch
import io

# Export directory configuration
EXPORT_DIR = "/tmp/protex-intelligence-file-exports"


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
        print("🚀 Launching Pyppeteer browser...", file=sys.stderr)
        browser = await launch({
            'headless': True,
            'executablePath': '/usr/bin/chromium',
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding'
            ]
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
                'bottom': '30mm',
                'left': '20mm'
            }),
            'displayHeaderFooter': True,
            'headerTemplate': '',
            'footerTemplate': '<div style="font-size: 8px; color: #666; text-align: right; width: 100%; margin: 0; padding-right: 20mm; font-family: Arial, Helvetica, sans-serif;">This content has been generated using Protex Intelligence. The output is intended to assist but may not always be accurate or complete. Please verify important information before acting upon it.</div>'
        }
        
        # Allow custom header/footer if specified, but keep watermark
        if options.get('displayHeaderFooter'):
            pdf_options['headerTemplate'] = options.get('headerTemplate', '')
            custom_footer = options.get('footerTemplate', '')
            if custom_footer:
                pdf_options['footerTemplate'] = f'{custom_footer}<div style="font-size: 8px; color: #666; text-align: right; width: 100%; margin: 5px 0 0; padding-right: 20mm; font-family: Arial, Helvetica, sans-serif;">This content has been generated using Protex Intelligence. The output is intended to assist but may not always be accurate or complete. Please verify important information before acting upon it.</div>'
        
        # Generate PDF
        print("📄 Generating PDF...", file=sys.stderr)
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
                print(f"Error closing browser: {close_error}", file=sys.stderr)
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
        print(f"✓ Export directory exists: {EXPORT_DIR}", file=sys.stderr)
    else:
        try:
            export_path.mkdir(parents=True, exist_ok=True)
            print(f"✓ Created export directory: {EXPORT_DIR}", file=sys.stderr)
        except Exception as e:
            print(f"✗ Failed to create export directory: {e}", file=sys.stderr)
            raise


async def write_pdf_to_file(pdf_content: bytes, filename: str) -> str:
    """Write PDF content to file system."""
    await ensure_export_directory()
    
    filepath = Path(EXPORT_DIR) / filename
    
    try:
        filepath.write_bytes(pdf_content)
        print(f"✓ File written: {filepath}", file=sys.stderr)
        return str(filepath)
    except Exception as e:
        print(f"✗ Failed to write file: {e}", file=sys.stderr)
        raise


# Create FastMCP server
mcp = FastMCP("pdf-export-mcp")


@mcp.tool()
async def pdf_export(
    html: str,
    css: str = None,
    filename: str = "output",
    description: str = None,
    options: Dict[str, Any] = None
) -> dict:
    """Export HTML to PDF format and save to filesystem.
    
    Args:
        html: HTML content to render as PDF
        css: Optional CSS to apply to the HTML
        filename: Filename for the exported file (without extension)
        description: Optional description of the file contents
        options: PDF generation options including format, orientation, margins, etc.
        
    Returns:
        Dictionary with export results including path and file info
    """
    try:
        # Validate input
        if not html or not isinstance(html, str):
            raise ValueError("HTML content must be provided as a string")
        
        if html.strip() == "":
            raise ValueError("HTML content cannot be empty")
        
        # Generate PDF
        print("🔄 Generating PDF from HTML...", file=sys.stderr)
        pdf_content = await generate_pdf(html, css, options or {})
        
        # Generate UUID and filename
        file_uuid = str(uuid.uuid4())
        sanitized_filename = "".join(c if c.isalnum() or c in "_-" else "_" for c in filename)
        full_filename = f"{sanitized_filename}_{file_uuid}.pdf"
        file_size = get_file_size_string(pdf_content)
        
        # Write PDF to file system
        filepath = await write_pdf_to_file(pdf_content, full_filename)
        
        print(f"✅ PDF generated: {full_filename} ({file_size})", file=sys.stderr)
        print(f"   Saved to: {filepath}", file=sys.stderr)
        
        # Return simplified response with essential information
        return {
            "path": full_filename,
            "filetype": "application/pdf",
            "filename": full_filename,
            "filesize": file_size,
        }
        
    except Exception as error:
        print(f"Error processing PDF export: {error}", file=sys.stderr)
        
        return {
            "success": False,
            "error": str(error),
        }


def cli_main():
    """CLI entry point."""
    mcp.run()


if __name__ == "__main__":
    cli_main()