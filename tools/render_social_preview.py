"""Rebuild the social-preview JPEG using Pillow and local DejaVu Sans fonts."""
from PIL import Image, ImageDraw, ImageFont, ImageOps
from pathlib import Path
root=Path(__file__).resolve().parents[1]
im=Image.new('RGB',(1200,630),'#f5f3ff'); d=ImageDraw.Draw(im)
photo=Image.open(root/'public/assets/28f837a14e625e87e471.jpg').convert('RGB')
im.paste(ImageOps.fit(photo,(470,630)),(730,0))
def font(size,bold=False):
 return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf',size)
d.rectangle((60,98,126,104),fill='#4830e6')
d.text((60,146),'Sheena Chan',font=font(62,True),fill='#08082c')
d.text((63,238),'UX Design & Research',font=font(36),fill='#4830e6')
d.text((63,321),'Thoughtful, human-centered',font=font(29),fill='#49475c')
d.text((63,364),'digital experiences.',font=font(29),fill='#49475c')
d.text((63,520),'sheenachan.com',font=font(27),fill='#08082c')
im.save(root/'public/assets/sheena-chan-social-preview.jpg',quality=92,optimize=True)
