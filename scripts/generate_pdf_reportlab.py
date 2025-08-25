#!/usr/bin/env python3
"""
PDF generation using ReportLab - pure Python solution with Chinese support.
"""

import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.colors import HexColor
import json
from datetime import datetime

def find_chinese_font():
    """Find available Chinese font on the system."""
    font_paths = [
        # macOS fonts
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        # Common downloaded fonts
        "/Library/Fonts/SimHei.ttf",
        "/Library/Fonts/SimSun.ttf",
    ]
    
    for font_path in font_paths:
        if Path(font_path).exists():
            return font_path
    return None

def setup_chinese_font():
    """Setup Chinese font for ReportLab."""
    font_path = find_chinese_font()
    if font_path:
        try:
            # Register the font
            pdfmetrics.registerFont(TTFont('Chinese', font_path))
            return 'Chinese'
        except:
            pass
    return 'Helvetica'  # Fallback to default

def markdown_to_reportlab(md_content, styles, chinese_font, config=None):
    """Convert markdown to ReportLab story elements with smart formatting."""
    
    # Default configuration for spacing
    if config is None:
        config = {
            'paragraph_spacing': 0.05 * cm,  # Reduced from 0.1cm
            'heading2_spacing': 0.08 * cm,   # Reduced from 0.1cm
            'heading1_spacing': 0.15 * cm,   # Reduced from 0.2cm
            'section_break_spacing': 0.3 * cm,  # Space for section breaks
            'max_consecutive_breaks': 1,      # Limit consecutive page breaks
            'min_content_for_page_break': 3,  # Min paragraphs before allowing page break
            'smart_separators': True,         # Enable smart separator handling
            'remove_redundant_content': True  # Remove duplicate titles
        }
    
    story = []
    
    # Create custom styles with Chinese font
    title_style = ParagraphStyle(
        'ChineseTitle',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=16,
        spaceAfter=12,
        textColor=HexColor('#2c3e50')
    )
    
    heading2_style = ParagraphStyle(
        'ChineseHeading2',
        parent=styles['Heading2'],
        fontName=chinese_font,
        fontSize=14,
        spaceAfter=6,
        textColor=HexColor('#34495e')
    )
    
    heading3_style = ParagraphStyle(
        'ChineseHeading3',
        parent=styles['Heading3'],
        fontName=chinese_font,
        fontSize=12,
        spaceAfter=4,
        textColor=HexColor('#34495e')
    )
    
    body_style = ParagraphStyle(
        'ChineseBody',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        firstLineIndent=20
    )
    
    # State tracking variables
    lines = md_content.split('\n')
    in_code_block = False
    code_buffer = []
    last_element_type = None
    consecutive_separators = 0
    content_since_break = 0
    seen_titles = set()
    last_title = None
    
    for i, line in enumerate(lines):
        # Skip image references
        if line.startswith('![') or 'img-' in line:
            continue
        
        # Skip single dots or empty placeholder content
        if line.strip() in ['.', '...', '•', '*', '-'] and config['remove_redundant_content']:
            continue
            
        # Handle code blocks
        if line.startswith('```'):
            in_code_block = not in_code_block
            if not in_code_block and code_buffer:
                # End of code block
                code_text = '<pre>' + '\n'.join(code_buffer) + '</pre>'
                story.append(Paragraph(code_text, styles['Code']))
                code_buffer = []
                last_element_type = 'code'
                content_since_break += 1
            continue
        
        if in_code_block:
            code_buffer.append(line)
            continue
        
        # Handle headers
        if line.startswith('# '):
            text = line[2:].strip()
            
            # Skip duplicate titles
            if config['remove_redundant_content'] and text in seen_titles:
                continue
            seen_titles.add(text)
            
            # Smart page break logic for top-level headers
            # Only add page break if there's been substantial content since last break
            if content_since_break > config['min_content_for_page_break'] and last_element_type != 'separator':
                story.append(PageBreak())
                content_since_break = 0
            
            story.append(Paragraph(text, title_style))
            story.append(Spacer(1, config['heading1_spacing']))
            last_element_type = 'h1'
            last_title = text
            content_since_break += 1
            
        elif line.startswith('## '):
            text = line[3:].strip()
            
            # Skip if it's the same as the last title (redundant)
            if config['remove_redundant_content'] and text == last_title:
                continue
                
            story.append(Paragraph(text, heading2_style))
            story.append(Spacer(1, config['heading2_spacing']))
            last_element_type = 'h2'
            content_since_break += 1
            
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, heading3_style))
            story.append(Spacer(1, config['heading2_spacing'] * 0.8))
            last_element_type = 'h3'
            content_since_break += 1
            
        elif line.startswith('---'):
            # Smart separator handling
            if config['smart_separators']:
                consecutive_separators += 1
                
                # Only process the first separator in a sequence
                if consecutive_separators == 1:
                    # Check if next non-empty line is a major header
                    is_chapter_break = False
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if lines[j].strip() and not lines[j].startswith('---'):
                            if lines[j].startswith('# '):
                                is_chapter_break = True
                            break
                    
                    # Only add page break for chapter transitions
                    if is_chapter_break and content_since_break > 2:
                        story.append(PageBreak())
                        content_since_break = 0
                    else:
                        # Just add some spacing for section breaks
                        story.append(Spacer(1, config['section_break_spacing']))
                    
                    last_element_type = 'separator'
            else:
                # Original behavior
                story.append(PageBreak())
                content_since_break = 0
                last_element_type = 'separator'
                
        elif line.strip():
            # Reset consecutive separator count
            consecutive_separators = 0
            
            # Regular paragraph
            text = line.strip()
            
            # Skip if it's repetitive content
            if config['remove_redundant_content'] and text == last_title:
                continue
            
            # Escape special ReportLab characters
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            
            # Convert markdown bold/italic
            text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
            text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
            
            story.append(Paragraph(text, body_style))
            
            # Add appropriate spacing based on context
            if last_element_type in ['h1', 'h2', 'h3']:
                # Less space after headers
                story.append(Spacer(1, config['paragraph_spacing'] * 0.5))
            else:
                story.append(Spacer(1, config['paragraph_spacing']))
            
            last_element_type = 'paragraph'
            content_since_break += 1
    
    return story

def generate_pdf_reportlab(input_file: Path, output_file: Path, config=None):
    """Generate PDF using ReportLab with smart formatting."""
    
    # Read markdown content
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Setup Chinese font
    chinese_font = setup_chinese_font()
    if chinese_font == 'Helvetica':
        print("Warning: Chinese font not found, using default font")
    else:
        print(f"Using Chinese font: {chinese_font}")
    
    # Create PDF
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Convert markdown to story with smart formatting
        story = markdown_to_reportlab(md_content, styles, chinese_font, config)
        
        # Build PDF
        doc.build(story)
        
        print(f"✅ PDF generated successfully: {output_file}")
        
        # Save state
        state_file = Path("data/state/pdf_generation_reportlab.json")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump({
                'success': True,
                'input_file': str(input_file),
                'output_file': str(output_file),
                'font_used': chinese_font,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        return True
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return False

def main():
    """Main function with support for configuration options."""
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate PDF from Markdown with smart formatting')
    parser.add_argument('input', help='Input markdown file')
    parser.add_argument('output', nargs='?', default='data/output/希望不是战略_部分章节.pdf',
                        help='Output PDF file (default: data/output/希望不是战略_部分章节.pdf)')
    parser.add_argument('--compact', action='store_true', 
                        help='Use compact spacing settings')
    parser.add_argument('--no-smart-separators', action='store_true',
                        help='Disable smart separator handling')
    parser.add_argument('--keep-redundant', action='store_true',
                        help='Keep redundant/duplicate content')
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_file = Path(args.output)
    
    # Build configuration based on arguments
    config = None
    if args.compact or args.no_smart_separators or args.keep_redundant:
        config = {
            'paragraph_spacing': 0.03 * cm if args.compact else 0.05 * cm,
            'heading2_spacing': 0.05 * cm if args.compact else 0.08 * cm,
            'heading1_spacing': 0.1 * cm if args.compact else 0.15 * cm,
            'section_break_spacing': 0.2 * cm if args.compact else 0.3 * cm,
            'max_consecutive_breaks': 1,
            'min_content_for_page_break': 3,
            'smart_separators': not args.no_smart_separators,
            'remove_redundant_content': not args.keep_redundant
        }
    
    success = generate_pdf_reportlab(input_file, output_file, config)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()