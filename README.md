# PDF Export MCP Server

A Model Context Protocol (MCP) server that provides PDF export functionality from HTML content. This server allows you to convert HTML (with optional CSS) to PDF format files.

## Features

- Convert HTML content to PDF format
- Optional CSS styling support
- Customizable page format (A4, Letter, Legal, Tabloid)
- Portrait/landscape orientation
- Configurable margins
- Header/footer support (basic)
- File size reporting
- UUID-based unique filenames
- Saves files to `/tmp/protex-intelligence-file-exports/`

## Installation

```bash
# Clone and install
git clone <repository-url>
cd pdf-export-mcp
uv pip install -e .
```

## Dependencies

This package uses `pyppeteer` (Python port of Puppeteer) for HTML to PDF conversion. Pyppeteer will automatically download a Chromium browser on first use.

## Usage

The server provides one tool:

### `pdf_export`

Exports HTML content to PDF format.

**Parameters:**
- `html` (required): HTML content to render as PDF
- `css` (optional): CSS to apply to the HTML
- `filename` (optional): Filename for the exported file (without extension), defaults to "output"
- `description` (optional): Description of the file contents
- `options` (optional): PDF generation options
  - `format`: Page format - "A4", "Letter", "Legal", "Tabloid" (default: "A4")
  - `orientation`: Page orientation - "portrait", "landscape" (default: "portrait")
  - `printBackground`: Print background graphics (default: true)
  - `margin`: Page margins object with top, right, bottom, left (default: "20mm" each)
  - `displayHeaderFooter`: Display header and footer (default: false)
  - `headerTemplate`: HTML template for header
  - `footerTemplate`: HTML template for footer

**Example:**
```json
{
  "html": "<h1>Hello World</h1><p>This is a test document.</p>",
  "css": "h1 { color: blue; } p { font-size: 14px; }",
  "filename": "test_document",
  "options": {
    "format": "A4",
    "orientation": "portrait",
    "margin": {
      "top": "25mm",
      "right": "25mm",
      "bottom": "25mm",
      "left": "25mm"
    }
  }
}
```

## Running the Server

```bash
pdf-export-mcp
```

## Development

```bash
# Install in development mode
uv pip install -e .

# Run tests (if available)
python -m pytest
```

## License

MIT
