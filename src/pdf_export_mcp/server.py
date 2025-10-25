#!/usr/bin/env python3
"""PDF Export MCP Server - Python implementation."""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
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


# Create MCP server
server = Server("pdf-export-mcp")


@server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="pdf_export",
            description="Export HTML to PDF format and save to filesystem",
            inputSchema={
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "HTML content to render as PDF",
                    },
                    "css": {
                        "type": "string",
                        "description": "Optional CSS to apply to the HTML",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Filename for the exported file (without extension)",
                        "default": "output",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the file contents",
                    },
                    "options": {
                        "type": "object",
                        "description": "PDF generation options",
                        "properties": {
                            "format": {
                                "type": "string",
                                "enum": ["A4", "Letter", "Legal", "Tabloid"],
                                "description": "Page format (default: A4)",
                                "default": "A4",
                            },
                            "orientation": {
                                "type": "string",
                                "enum": ["portrait", "landscape"],
                                "description": "Page orientation (default: portrait)",
                                "default": "portrait",
                            },
                            "printBackground": {
                                "type": "boolean",
                                "description": "Print background graphics (default: true)",
                                "default": True,
                            },
                            "margin": {
                                "type": "object",
                                "description": "Page margins",
                                "properties": {
                                    "top": {"type": "string", "default": "20mm"},
                                    "right": {"type": "string", "default": "20mm"},
                                    "bottom": {"type": "string", "default": "20mm"},
                                    "left": {"type": "string", "default": "20mm"},
                                },
                            },
                            "displayHeaderFooter": {
                                "type": "boolean",
                                "description": "Display header and footer (default: false)",
                                "default": False,
                            },
                            "headerTemplate": {
                                "type": "string",
                                "description": "HTML template for the header",
                            },
                            "footerTemplate": {
                                "type": "string",
                                "description": "HTML template for the footer",
                            },
                        },
                    },
                },
                "required": ["html"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any]
) -> List[types.TextContent]:
    """Handle tool calls."""
    if name == "pdf_export":
        try:
            html = arguments.get("html")
            css = arguments.get("css")
            filename = arguments.get("filename", "output")
            description = arguments.get("description")
            options = arguments.get("options", {})
            
            # Validate input
            if not html or not isinstance(html, str):
                raise ValueError("HTML content must be provided as a string")
            
            if html.strip() == "":
                raise ValueError("HTML content cannot be empty")
            
            # Generate PDF
            print("🔄 Generating PDF from HTML...", file=sys.stderr)
            pdf_content = await generate_pdf(html, css, options)
            
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
            result = {
                "path": full_filename,
                "filetype": "application/pdf",
                "filename": full_filename,
                "filesize": file_size,
            }
            
            return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
            
        except Exception as error:
            print(f"Error processing PDF export: {error}", file=sys.stderr)
            
            error_result = {
                "success": False,
                "error": str(error),
            }
            
            return [types.TextContent(type="text", text=json.dumps(error_result, indent=2))]
    
    raise ValueError(f"Unknown tool: {name}")


async def main():
    """Main server function."""
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        print("PDF Export MCP Server running on stdio", file=sys.stderr)
        await server.run(
            read_stream,
            write_stream,
            NotificationOptions(
                tools_changed=False,
                resources_changed=False,
                prompts_changed=False
            ),
        )


def cli_main():
    """CLI entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()