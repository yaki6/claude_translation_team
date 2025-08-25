#!/usr/bin/env python3
"""
Professional PDF generation with original book styling.
Replicates the teal color scheme and clean layout of the original.
"""

import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle, ListStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, 
    Table, TableStyle, ListFlowable, ListItem,
    KeepTogether, Flowable
)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import HexColor, Color
from reportlab.lib import colors
from reportlab.pdfgen import canvas
import json
from datetime import datetime

# Define the color scheme from the original book
COLORS = {
    'teal': HexColor('#008B8B'),        # Main teal color for headers
    'teal_dark': HexColor('#006666'),   # Darker teal for emphasis
    'blue_link': HexColor('#0066CC'),   # Blue for links/references
    'black': HexColor('#000000'),       # Black for body text
    'gray': HexColor('#666666'),        # Gray for secondary text
    'white': colors.white,              # White for header text
    'light_gray': HexColor('#F5F5F5'),  # Light gray for backgrounds
}

class TealHeaderCanvas(canvas.Canvas):
    """Custom canvas to add teal header bar to each page."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        self.page_num = 0
        
    def showPage(self):
        self.page_num += 1
        self.pages.append(dict(self.__dict__))
        self._startPage()
        
    def save(self):
        for page in self.pages:
            self.__dict__.update(page)
            self.draw_header()
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
        
    def draw_header(self):
        """Draw the teal header bar at the top of each page."""
        self.saveState()
        
        # Draw teal header bar
        self.setFillColor(COLORS['teal'])
        self.rect(0, A4[1] - 2.5*cm, A4[0], 2.5*cm, fill=1, stroke=0)
        
        # Add header text
        self.setFillColor(COLORS['white'])
        self.setFont("Helvetica-Bold", 10)
        
        # Left side - Book title
        self.drawString(2*cm, A4[1] - 1.5*cm, "希望不是战略")
        
        # Right side - Page number
        page_text = f"第 {self.page_num} 页"
        self.drawRightString(A4[0] - 2*cm, A4[1] - 1.5*cm, page_text)
        
        self.restoreState()

class HorizontalLine(Flowable):
    """Custom flowable for horizontal lines."""
    
    def __init__(self, width, color=COLORS['teal'], thickness=1):
        Flowable.__init__(self)
        self.width = width
        self.color = color
        self.thickness = thickness
        
    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)
        
    def wrap(self, availWidth, availHeight):
        return (self.width, self.thickness)

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
            pdfmetrics.registerFont(TTFont('Chinese', font_path))
            return 'Chinese'
        except:
            pass
    return 'Helvetica'

def create_professional_styles(chinese_font):
    """Create styles matching the original book design."""
    styles = {}
    
    # Main title style (large teal)
    styles['Title'] = ParagraphStyle(
        'Title',
        fontName=chinese_font,
        fontSize=20,
        leading=24,
        textColor=COLORS['teal'],
        alignment=TA_LEFT,
        spaceAfter=20,
        spaceBefore=10,
        leftIndent=0,
        rightIndent=0,
    )
    
    # Chapter heading style (large teal, all caps effect)
    styles['ChapterTitle'] = ParagraphStyle(
        'ChapterTitle',
        fontName=chinese_font,
        fontSize=24,
        leading=28,
        textColor=COLORS['teal'],
        alignment=TA_CENTER,
        spaceAfter=30,
        spaceBefore=20,
    )
    
    # Section heading style (medium teal)
    styles['Heading1'] = ParagraphStyle(
        'Heading1',
        fontName=chinese_font,
        fontSize=18,
        leading=22,
        textColor=COLORS['teal'],
        alignment=TA_LEFT,
        spaceAfter=15,
        spaceBefore=20,
    )
    
    # Subsection heading style (smaller teal)
    styles['Heading2'] = ParagraphStyle(
        'Heading2',
        fontName=chinese_font,
        fontSize=14,
        leading=18,
        textColor=COLORS['teal'],
        alignment=TA_LEFT,
        spaceAfter=10,
        spaceBefore=15,
    )
    
    # Subsubsection heading style
    styles['Heading3'] = ParagraphStyle(
        'Heading3',
        fontName=chinese_font,
        fontSize=12,
        leading=16,
        textColor=COLORS['teal_dark'],
        alignment=TA_LEFT,
        spaceAfter=8,
        spaceBefore=10,
    )
    
    # Body text style
    styles['Body'] = ParagraphStyle(
        'Body',
        fontName=chinese_font,
        fontSize=11,
        leading=16,
        textColor=COLORS['black'],
        alignment=TA_JUSTIFY,
        spaceAfter=8,
        firstLineIndent=20,
    )
    
    # Quote style (italic with blue text)
    styles['Quote'] = ParagraphStyle(
        'Quote',
        fontName=chinese_font,
        fontSize=11,
        leading=16,
        textColor=COLORS['blue_link'],
        alignment=TA_LEFT,
        leftIndent=20,
        rightIndent=20,
        spaceAfter=10,
        spaceBefore=10,
    )
    
    # Link style
    styles['Link'] = ParagraphStyle(
        'Link',
        fontName=chinese_font,
        fontSize=11,
        leading=16,
        textColor=COLORS['blue_link'],
        alignment=TA_LEFT,
    )
    
    # Bullet list style
    styles['Bullet'] = ParagraphStyle(
        'Bullet',
        fontName=chinese_font,
        fontSize=11,
        leading=16,
        textColor=COLORS['black'],
        alignment=TA_LEFT,
        leftIndent=20,
        spaceAfter=5,
    )
    
    # Number list style
    styles['Number'] = ParagraphStyle(
        'Number',
        fontName=chinese_font,
        fontSize=11,
        leading=16,
        textColor=COLORS['black'],
        alignment=TA_LEFT,
        leftIndent=20,
        spaceAfter=5,
    )
    
    return styles

def markdown_to_professional_pdf(md_content, styles, chinese_font):
    """Convert markdown to professionally styled ReportLab elements."""
    story = []
    lines = md_content.split('\n')
    
    in_code_block = False
    in_list = False
    list_items = []
    list_type = None
    code_buffer = []
    seen_titles = set()
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip image references
        if line.startswith('![') or 'img-' in line:
            i += 1
            continue
        
        # Skip single dots or placeholder content
        if line.strip() in ['.', '...', '•']:
            i += 1
            continue
            
        # Handle code blocks
        if line.startswith('```'):
            in_code_block = not in_code_block
            if not in_code_block and code_buffer:
                code_text = '\n'.join(code_buffer)
                story.append(Paragraph(f'<pre>{code_text}</pre>', styles['Body']))
                code_buffer = []
            i += 1
            continue
        
        if in_code_block:
            code_buffer.append(line)
            i += 1
            continue
        
        # Handle lists
        if line.strip().startswith(('- ', '* ', '+ ')):
            if not in_list:
                in_list = True
                list_type = 'bullet'
                list_items = []
            text = line.strip()[2:]
            list_items.append(text)
            i += 1
            # Check if next line continues the list
            if i < len(lines) and not lines[i].strip().startswith(('- ', '* ', '+ ', '1.', '2.', '3.')):
                # End of list
                bullet_list = []
                for item in list_items:
                    bullet_list.append(ListItem(Paragraph(item, styles['Bullet']), 
                                               bulletColor=COLORS['teal'],
                                               value='•'))
                story.append(ListFlowable(bullet_list, bulletType='bullet'))
                story.append(Spacer(1, 0.3*cm))
                in_list = False
                list_items = []
            continue
            
        # Handle numbered lists
        elif re.match(r'^\d+\.\s', line.strip()):
            if not in_list:
                in_list = True
                list_type = 'number'
                list_items = []
            text = re.sub(r'^\d+\.\s+', '', line.strip())
            list_items.append(text)
            i += 1
            # Check if next line continues the list
            if i < len(lines) and not re.match(r'^\d+\.\s', lines[i].strip()):
                # End of list
                number_list = []
                for idx, item in enumerate(list_items, 1):
                    number_list.append(ListItem(Paragraph(item, styles['Number']),
                                               bulletColor=COLORS['teal'],
                                               value=str(idx)))
                story.append(ListFlowable(number_list, bulletType='1'))
                story.append(Spacer(1, 0.3*cm))
                in_list = False
                list_items = []
            continue
        
        # Handle headers
        if line.startswith('# '):
            text = line[2:].strip()
            if text not in seen_titles:
                seen_titles.add(text)
                story.append(PageBreak())
                story.append(Paragraph(text.upper(), styles['ChapterTitle']))
                story.append(HorizontalLine(width=15*cm, color=COLORS['teal'], thickness=2))
                story.append(Spacer(1, 0.5*cm))
            i += 1
            continue
            
        elif line.startswith('## '):
            text = line[3:].strip()
            story.append(Paragraph(text.upper(), styles['Heading1']))
            story.append(Spacer(1, 0.2*cm))
            i += 1
            continue
            
        elif line.startswith('### '):
            text = line[4:].strip()
            story.append(Paragraph(text, styles['Heading2']))
            story.append(Spacer(1, 0.15*cm))
            i += 1
            continue
            
        elif line.startswith('#### '):
            text = line[5:].strip()
            story.append(Paragraph(text, styles['Heading3']))
            story.append(Spacer(1, 0.1*cm))
            i += 1
            continue
        
        # Handle horizontal rules as section breaks
        elif line.startswith('---'):
            # Check if this is before a chapter heading
            if i + 1 < len(lines) and lines[i + 1].startswith('# '):
                # Skip - will be handled by chapter heading
                pass
            else:
                story.append(Spacer(1, 0.3*cm))
                story.append(HorizontalLine(width=10*cm, color=COLORS['light_gray'], thickness=0.5))
                story.append(Spacer(1, 0.3*cm))
            i += 1
            continue
            
        # Handle quotes (lines starting with >)
        elif line.startswith('>'):
            text = line[1:].strip()
            if text:
                # Process markdown formatting
                text = process_markdown_formatting(text)
                story.append(Paragraph(f'"{text}"', styles['Quote']))
                story.append(Spacer(1, 0.2*cm))
            i += 1
            continue
            
        # Handle regular paragraphs
        elif line.strip():
            text = line.strip()
            # Process markdown formatting
            text = process_markdown_formatting(text)
            
            # Check if this looks like a reference or link
            if 'http' in text or re.search(r'\[.*?\]\(.*?\)', text):
                # Convert markdown links to HTML
                text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', 
                             r'<a href="\2" color="blue">\1</a>', text)
                story.append(Paragraph(text, styles['Link']))
            else:
                story.append(Paragraph(text, styles['Body']))
            story.append(Spacer(1, 0.15*cm))
            i += 1
            continue
        
        i += 1
    
    return story

def process_markdown_formatting(text):
    """Process markdown bold, italic, and other formatting."""
    # Escape special ReportLab characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Convert markdown bold to HTML
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Convert markdown italic to HTML
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_', r'<i>\1</i>', text)
    
    # Convert markdown code to HTML
    text = re.sub(r'`(.+?)`', r'<font name="Courier">\1</font>', text)
    
    return text

def generate_professional_pdf(input_file: Path, output_file: Path):
    """Generate professional PDF matching original book design."""
    
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
    
    # Create professional styles
    styles = create_professional_styles(chinese_font)
    
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create document with custom canvas
        doc = SimpleDocTemplate(
            str(output_file),
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=3.5*cm,  # Extra space for header
            bottomMargin=2*cm,
            title="希望不是战略",
            author="克里斯蒂安·安德伍德 尤尔根·韦根德",
        )
        
        # Convert markdown to story
        story = markdown_to_professional_pdf(md_content, styles, chinese_font)
        
        # Build PDF with custom canvas
        doc.build(story, canvasmaker=TealHeaderCanvas)
        
        print(f"✅ Professional PDF generated successfully: {output_file}")
        
        # Save state
        state_file = Path("data/state/pdf_generation_professional.json")
        state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(state_file, 'w') as f:
            json.dump({
                'success': True,
                'input_file': str(input_file),
                'output_file': str(output_file),
                'font_used': chinese_font,
                'timestamp': datetime.now().isoformat(),
                'style': 'professional_teal'
            }, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python generate_pdf_professional.py <input.md> [output.pdf]")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    else:
        output_file = Path("data/output/希望不是战略_专业版.pdf")
    
    success = generate_professional_pdf(input_file, output_file)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()