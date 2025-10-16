#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { v4 as uuidv4 } from 'uuid';
import { promises as fs } from 'fs';
import path from 'path';
import puppeteer from 'puppeteer';

// Export directory configuration
const EXPORT_DIR = '/tmp/protex-intelligence-file-exports';

/**
 * Calculate file size string from buffer
 */
function getFileSizeString(buffer) {
  const bytes = buffer.length;
  const kb = Math.ceil(bytes / 1024);
  return kb < 1024 ? `${kb} KB` : `${(kb / 1024).toFixed(2)} MB`;
}

/**
 * Ensure export directory exists, create if it doesn't
 */
async function ensureExportDirectory() {
  try {
    await fs.access(EXPORT_DIR);
    console.error(`✓ Export directory exists: ${EXPORT_DIR}`);
  } catch (error) {
    try {
      await fs.mkdir(EXPORT_DIR, { recursive: true });
      console.error(`✓ Created export directory: ${EXPORT_DIR}`);
    } catch (mkdirError) {
      console.error(`✗ Failed to create export directory: ${mkdirError.message}`);
      throw mkdirError;
    }
  }
}

/**
 * Write PDF buffer to file system
 */
async function writePDFToFile(pdfBuffer, filename) {
  await ensureExportDirectory();

  const filepath = path.join(EXPORT_DIR, filename);

  try {
    await fs.writeFile(filepath, pdfBuffer);
    console.error(`✓ File written: ${filepath}`);
    return filepath;
  } catch (error) {
    console.error(`✗ Failed to write file: ${error.message}`);
    throw error;
  }
}

/**
 * Generate PDF from HTML using Puppeteer
 */
async function generatePDF(html, css, options = {}) {
  let browser;

  try {
    // Combine HTML and CSS if CSS is provided
    let fullHtml = html;
    if (css) {
      if (html.includes('<head>')) {
        fullHtml = html.replace('<head>', `<head><style>${css}</style>`);
      } else if (html.includes('<html>')) {
        fullHtml = html.replace('<html>', `<html><head><style>${css}</style></head>`);
      } else {
        fullHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>${css}</style>
</head>
<body>
${html}
</body>
</html>`;
      }
    }

    // Ensure fullHtml has basic HTML structure
    if (!fullHtml.includes('<!DOCTYPE') && !fullHtml.includes('<html')) {
      fullHtml = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
</head>
<body>
${fullHtml}
</body>
</html>`;
    }

    // Launch Puppeteer
    console.error('Launching Puppeteer browser...');
    browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    });

    const page = await browser.newPage();

    // Set content
    await page.setContent(fullHtml, {
      waitUntil: 'networkidle0',
    });

    // Prepare PDF options
    const pdfOptions = {
      format: options.format || 'A4',
      landscape: options.orientation === 'landscape',
      printBackground: options.printBackground !== false,
      margin: options.margin || {
        top: '20mm',
        right: '20mm',
        bottom: '20mm',
        left: '20mm',
      },
    };

    // Add header/footer if specified
    if (options.displayHeaderFooter) {
      pdfOptions.displayHeaderFooter = true;
      pdfOptions.headerTemplate = options.headerTemplate || '';
      pdfOptions.footerTemplate = options.footerTemplate || '';
    }

    // Generate PDF to buffer
    console.error('Generating PDF...');
    const pdfBytes = await page.pdf(pdfOptions);
    const pdfBuffer = Buffer.from(pdfBytes);

    // Close browser
    await browser.close();

    return pdfBuffer;
  } catch (error) {
    // Ensure browser is closed on error
    if (browser) {
      try {
        await browser.close();
      } catch (closeError) {
        console.error('Error closing browser:', closeError);
      }
    }
    throw error;
  }
}

// Create MCP server
const server = new Server(
  {
    name: 'pdf-export-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: 'pdf_export',
        description: 'Export HTML to PDF format and save to filesystem',
        inputSchema: {
          type: 'object',
          properties: {
            html: {
              type: 'string',
              description: 'HTML content to render as PDF',
            },
            css: {
              type: 'string',
              description: 'Optional CSS to apply to the HTML',
            },
            filename: {
              type: 'string',
              description: 'Filename for the exported file (without extension)',
              default: 'output',
            },
            description: {
              type: 'string',
              description: 'Optional description of the file contents',
            },
            options: {
              type: 'object',
              description: 'PDF generation options',
              properties: {
                format: {
                  type: 'string',
                  enum: ['A4', 'Letter', 'Legal', 'Tabloid'],
                  description: 'Page format (default: A4)',
                  default: 'A4',
                },
                orientation: {
                  type: 'string',
                  enum: ['portrait', 'landscape'],
                  description: 'Page orientation (default: portrait)',
                  default: 'portrait',
                },
                printBackground: {
                  type: 'boolean',
                  description: 'Print background graphics (default: true)',
                  default: true,
                },
                margin: {
                  type: 'object',
                  description: 'Page margins',
                  properties: {
                    top: { type: 'string', default: '20mm' },
                    right: { type: 'string', default: '20mm' },
                    bottom: { type: 'string', default: '20mm' },
                    left: { type: 'string', default: '20mm' },
                  },
                },
                displayHeaderFooter: {
                  type: 'boolean',
                  description: 'Display header and footer (default: false)',
                  default: false,
                },
                headerTemplate: {
                  type: 'string',
                  description: 'HTML template for the header',
                },
                footerTemplate: {
                  type: 'string',
                  description: 'HTML template for the footer',
                },
              },
            },
          },
          required: ['html'],
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === 'pdf_export') {
    try {
      const {
        html,
        css,
        filename = 'output',
        description,
        options = {},
      } = args;

      // Validate input
      if (!html || typeof html !== 'string') {
        throw new Error('HTML content must be provided as a string');
      }

      if (html.trim().length === 0) {
        throw new Error('HTML content cannot be empty');
      }

      // Generate PDF
      const pdfBuffer = await generatePDF(html, css, options);

      // Generate UUID and filename
      const uuid = uuidv4();
      const sanitizedFilename = filename.replace(/[^a-z0-9_-]/gi, '_');
      const fullFilename = `${sanitizedFilename}_${uuid}.pdf`;
      const fileSize = getFileSizeString(pdfBuffer);

      // Write PDF to file system
      const filepath = await writePDFToFile(pdfBuffer, fullFilename);

      console.error(`✅ PDF generated: ${fullFilename} (${fileSize})`);
      console.error(`   Saved to: ${filepath}`);

      // Return simplified response with essential information
      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                path: fullFilename,
                filetype: 'application/pdf',
                filename: fullFilename,
                filesize: fileSize,
              },
              null,
              2
            ),
          },
        ],
      };
    } catch (error) {
      console.error('Error processing PDF export:', error);

      return {
        content: [
          {
            type: 'text',
            text: JSON.stringify(
              {
                success: false,
                error: error.message || 'Unknown error',
              },
              null,
              2
            ),
          },
        ],
        isError: true,
      };
    }
  }

  throw new Error(`Unknown tool: ${name}`);
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('PDF Export MCP Server running on stdio');
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
