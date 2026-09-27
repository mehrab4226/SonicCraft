"""Build the CSE 220 presentation PDF and inspectable page renders."""
from pathlib import Path
import sys
import json
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / '.cache/presentation-deps'))
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.graphics import renderPDF
from reportlab.lib.utils import ImageReader
from svglib.svglib import svg2rlg
import pymupdf as fitz
from PIL import Image, ImageDraw

ASSETS = ROOT / 'Presentation/assets'
OUT = ROOT / 'output/pdf'
BUILD = ROOT / '.cache/presentation-revised'
OUT.mkdir(parents=True, exist_ok=True)
BUILD.mkdir(parents=True, exist_ok=True)
PDF=OUT/'SonicCraft_CSE220_Final_Presentation.pdf'
W,H=960,540
BG='#faf8f3'; FG='#202c35'; AMBER='#966016'; CORAL='#b04b3c'
MUTED='#52616b'; LINE='#d8dedc'; LIGHT='#faf8f3'; INK='#202c35'; GREY='#52616b'
for name,file in [('Segoe','segoeui.ttf'),('SegoeBold','segoeuib.ttf'),('SegoeLight','segoeuil.ttf'),('Mono','consola.ttf')]:
    pdfmetrics.registerFont(TTFont(name,'C:/Windows/Fonts/'+file))
c=canvas.Canvas(str(PDF),pagesize=(W,H),pageCompression=1)
c.setTitle('SonicCraft | CSE 220 Final Project Evaluation')
c.setAuthor('Md Mehrab Hossain (2305108); Mahbubul Islam Mahi (2305116)')
c.setSubject('SonicCraft audio editor: features, design and live workflow')
c.setCreator('SonicCraft presentation builder')
c.showOutline()
PAGE=0; DARK=True; QA=[]; TITLES=[]

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

def page(title,subtitle='',dark=True,source='',show_title=True,footer=True):
    global PAGE,DARK
    if PAGE:c.showPage()
    PAGE+=1;DARK=dark;TITLES.append(title)
    rect(0,0,W,H,BG if dark else LIGHT)
    c.bookmarkPage('page'+str(PAGE))
    c.addOutlineEntry(title,'page'+str(PAGE),0,False)
    if show_title:text(title,54,43,38,'SegoeBold',w=852,max_lines=1)
    if subtitle:text(subtitle,54,104,20,col=MUTED if dark else GREY,w=852,max_lines=2)
    if footer:
        line(54,498,906,498,LINE if dark else '#d3ccc1',.6)
        if source:text(source,54,511,9.5,col=MUTED if dark else GREY,w=785,max_lines=1)
        text(f'{PAGE:02d}',878,510,12,'Mono',AMBER if dark else GREY)

def bullet(body,x,y,width=255,size=20):
    c.setFillColor(color(AMBER))
    c.circle(x+5,H-y-12,5,stroke=0,fill=1)
    text(body,x+22,y,size,col=FG,w=width,max_lines=2,leading=size*1.32)

def feature(title,summary,category,points,plot,source,detail=''):
    page(title,summary,source=source)
    label(category,54,157,size=12)
    for i,point in enumerate(points):bullet(point,54,203+i*77)
    svg(plot,350,161,565,289)
    if detail:text(detail,369,456,13,col=MUTED,w=529,max_lines=2)


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
print(f'Created {PDF} with {len(doc)} presentation slides.')
print(f'Rendered every page in {BUILD}')
