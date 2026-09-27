"""Build the CSE 220 evaluation PDF and inspectable page renders.

Run prepare_presentation_assets.py first. PDF-only delivery uses ReportLab,
Matplotlib's equation typesetting, vector plot assets, and PyMuPDF rendering.
"""
from pathlib import Path
from io import BytesIO
import sys
import json
import math
import os
import re

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / '.cache/presentation-deps'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.graphics import renderPDF
from reportlab.lib.utils import ImageReader
from svglib.svglib import svg2rlg
from matplotlib.mathtext import math_to_image
from matplotlib.font_manager import FontProperties
import pymupdf as fitz
from PIL import Image, ImageDraw

ASSETS = ROOT / 'Presentation/assets'
OUT = ROOT / 'output/pdf'
BUILD = ROOT / '.cache/presentation-revised'
OUT.mkdir(parents=True, exist_ok=True)
BUILD.mkdir(parents=True, exist_ok=True)
RESULTS=json.loads((ASSETS/'measurements.json').read_text())
PDF=OUT/'SonicCraft_CSE220_Final_Presentation.pdf'
W,H=960,540
BG='#141416'; FG='#f4eee4'; AMBER='#e6bd78'; CORAL='#e5a093'
MUTED='#bcb7af'; LINE='#3d3b3a'; LIGHT='#f2eee6'; INK='#222328'; GREY='#68645f'
for name,file in [('Segoe','segoeui.ttf'),('SegoeBold','segoeuib.ttf'),('SegoeLight','segoeuil.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
c=canvas.Canvas(str(PDF),pagesize=(W,H),pageCompression=1)
c.setTitle('SonicCraft | CSE 220 Final Project Evaluation')
c.setAuthor('Md Mehrab Hossain (2305108); Mahbubul Islam Mahi (2305115)')
c.setSubject('A short overview of SonicCraft features and their Signals and Systems connections')
c.setCreator('SonicCraft presentation builder')
c.showOutline()
PAGE=0; A_INDEX=0; DARK=True; QA=[]; TITLES=[]

def color(hexcode): return HexColor(hexcode)

def rect(x,y,w,h,fill,stroke=None,r=0):
    c.setFillColor(color(fill));c.setStrokeColor(color(stroke or fill))
    if r:c.roundRect(x,H-y-h,w,h,r,stroke=bool(stroke),fill=1)
    else:c.rect(x,H-y-h,w,h,stroke=bool(stroke),fill=1)

def line(x1,y1,x2,y2,col=LINE,width=1):
    c.setStrokeColor(color(col));c.setLineWidth(width);c.line(x1,H-y1,x2,H-y2)

def text(s,x,y,size=22,font='Segoe',col=None,w=None,leading=None,max_lines=None):
    col=col or (FG if DARK else INK)
    leading=leading or size*1.28
    lines=[]
    for paragraph in str(s).split('\n'):
        if w is None:
            lines.append(paragraph);continue
        current=''
        for word in paragraph.split():
            trial=(current+' '+word).strip()
            if current and pdfmetrics.stringWidth(trial,font,size)>w:
                lines.append(current);current=word
            else:current=trial
        lines.append(current)
    if max_lines is not None and len(lines)>max_lines:
        raise ValueError(f'Page {PAGE}: too many lines for {s!r}: {len(lines)}')
    for i,entry in enumerate(lines):
        width=pdfmetrics.stringWidth(entry,font,size)
        if w is not None and width>w+.1:
            raise ValueError(f'Page {PAGE}: text too wide: {entry!r}')
        yy=y+i*leading
        if x<0 or x+width>W+1 or yy+size>H:
            raise ValueError(f'Page {PAGE}: out of bounds: {entry!r}')
        c.setFont(font,size);c.setFillColor(color(col));c.drawString(x,H-yy-size*.82,entry)
        QA.append({'page':PAGE,'text':entry,'box':[x,yy,x+width,yy+size]})
    return len(lines)*leading

def label(s,x,y,col=None,size=12):
    return text(s.upper(),x,y,size,'SegoeBold',col or (AMBER if DARK else '#88612b'))

def equation(expr,x,y,w=300,h=65,col=None):
    data=BytesIO()
    math_to_image('$'+expr+'$',data,prop=FontProperties(size=28),format='svg',color=col or (FG if DARK else INK))
    # MathText's SVG includes an opaque white figure patch. Remove that patch
    # so the equation remains a clean vector layer over the slide background.
    svg_data=re.sub(rb'<g id="patch_1">.*?</g>',b'',data.getvalue(),flags=re.S)
    drawing=svg2rlg(BytesIO(svg_data))
    scale=min(w/drawing.width,h/drawing.height)
    c.saveState();c.translate(x,H-y-drawing.height*scale);c.scale(scale,scale)
    renderPDF.draw(drawing,c,0,0);c.restoreState()

def svg(name,x,y,w,h):
    drawing=svg2rlg(str(ASSETS/(name+'.svg')))
    scale=min(w/drawing.width,h/drawing.height)
    c.saveState();c.translate(x,H-y-drawing.height*scale);c.scale(scale,scale)
    renderPDF.draw(drawing,c,0,0);c.restoreState()

def image(name,x,y,w,h):
    path=ASSETS/name
    with Image.open(path) as im:
        iw,ih=im.size
    scale=min(w/iw,h/ih)
    c.drawImage(ImageReader(str(path)),x,H-y-ih*scale,iw*scale,ih*scale,mask='auto')

def arrow(x1,y1,x2,y2,col=AMBER):
    line(x1,y1,x2,y2,col,1.5)
    a=math.atan2(y2-y1,x2-x1)
    for angle in (a+2.65,a-2.65):
        line(x2,y2,x2+8*math.cos(angle),y2+8*math.sin(angle),col,1.5)

def page(title,subtitle='',dark=True,source='',appendix=None,show_title=True):
    global PAGE,A_INDEX,DARK
    if PAGE:c.showPage()
    PAGE+=1;DARK=dark;TITLES.append(title)
    if appendix:
        A_INDEX+=1
        appendix=A_INDEX
    rect(0,0,W,H,BG if dark else LIGHT)
    c.bookmarkPage('page'+str(PAGE))
    c.addOutlineEntry(('A'+str(appendix)+'. ' if appendix else '')+title,'page'+str(PAGE),0,False)
    if appendix:
        label('Q&A reference',54,24,col=MUTED if dark else GREY,size=10)
    if show_title:text(title,54,50 if appendix else 43,38,'SegoeBold',w=852,max_lines=1)
    if subtitle:text(subtitle,54,104 if not appendix else 108,20,col=MUTED if dark else GREY,w=852,max_lines=2)
    line(54,498,906,498,LINE if dark else '#d3ccc1',.6)
    if source:text(source,54,511,9.5,col=MUTED if dark else GREY,w=785,max_lines=1)
    text(('A'+str(appendix)) if appendix else f'{PAGE:02d}',878,510,12,'Mono',AMBER if dark else GREY)

def feature(title,summary,theory,description,expr,plot,source,detail=None):
    page(title,summary,source=source)
    label('Theory connection',54,172)
    text(theory,54,199,27,'SegoeBold',w=286,max_lines=2)
    text(description,54,285,22,col=MUTED,w=276,max_lines=3)
    if expr:equation(expr,54,385,284,59)
    svg(plot,350,170,565,284)
    if detail:text(detail,369,459,13,col=MUTED,w=532,max_lines=2)


exec((ROOT / 'Presentation/presentation_slides.py').read_text(encoding='utf-8'))

c.save()
(BUILD/'text-layout.json').write_text(json.dumps(QA,indent=2),encoding='utf-8')
(BUILD/'slide-titles.json').write_text(json.dumps(TITLES,indent=2),encoding='utf-8')
doc=fitz.open(PDF)
thumbnails=[]
for i,p in enumerate(doc):
    pix=p.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
    pix.save(str(BUILD/f'slide-{i+1:02d}.png'))
    im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
    im.thumbnail((480,270))
    thumb=Image.new('RGB',(500,304),'#29292d');thumb.paste(im,(10,10))
    ImageDraw.Draw(thumb).text((12,283),f'{i+1:02d}  {TITLES[i]}',fill='white')
    thumbnails.append(thumb)
for start in range(0,len(thumbnails),8):
    batch=thumbnails[start:start+8]
    sheet=Image.new('RGB',(1000,304*math.ceil(len(batch)/2)),'#29292d')
    for i,thumb in enumerate(batch):sheet.paste(thumb,((i%2)*500,(i//2)*304))
    sheet.save(BUILD/f'contact-{start//8+1}.png')
print(f'Created {PDF} with 13 main slides and {len(doc)-13} Q&A references.')
print(f'Rendered every page in {BUILD}')
