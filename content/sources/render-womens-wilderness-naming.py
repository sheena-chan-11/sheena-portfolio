#!/usr/bin/env python3
"""Rebuild the clearly-labelled PROPOSED naming mockup from the user recording.

Developer-only dependencies: ffmpeg, numpy, opencv-python-headless, Pillow,
fonttools[woff]. No application dependencies. Source recording is never changed.
Usage: python render-womens-wilderness-naming.py SOURCE.MP4 --output-dir /tmp/ww-naming
Font is cached outside the repository; its upstream URL and SHA are in the report.
The resulting two silent FFV1/MKV files have one shared 30fps timeline and can be
composited into a single comparison stream without synchronization drift.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_URL = 'https://womenswilderness.org/wp-content/uploads/elementor/google-fonts/fonts/sourcesanspro-6xk3dsbykcsv-lcoeqqfx1ryoo3qok7l.woff2'
W, H, FPS = 600, 1298, 30
BG = np.array([0., 34., 74.])
MAPPING = {
    'PARTNERSHIP & CUSTOM PROGRAMS': 'PARTNERSHIP & CUSTOM COURSES',
    'ADULT PROGRAMS': 'ADULT COURSES',
    'YOUTH PROGRAMS': 'YOUTH COURSES',
    'All Adult Programs': 'All Adult Courses',
    'All Youth Programs': 'All Youth Courses',
}

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''): h.update(chunk)
    return h.hexdigest()

def grab(cap, seconds):
    cap.set(cv2.CAP_PROP_POS_FRAMES, round(seconds * FPS))
    ok, im = cap.read()
    assert ok
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)

def purple(im):
    a = im.astype(float)
    return ((a[...,0] - a[...,1] > 30) & (a[...,2] - a[...,1] > 25)).astype(np.float32)

def glyph(text, size, width=220):
    # Supersampling preserves subpixel antialiasing instead of integer-font jumps.
    s = 16
    font = ImageFont.truetype(str(FONT), round(size * s))
    layer = Image.new('L', (width*s, 45*s))
    ImageDraw.Draw(layer).text((0,0), text, font=font, fill=255, anchor='lt')
    return np.asarray(layer.resize((width,45), Image.Resampling.LANCZOS), dtype=np.float32)/255

def y_match(field, template, lo=72, hi=1298):
    roi = field[lo:hi]
    if roi.shape[0] < template.shape[0]: return 0., 0.
    result = cv2.matchTemplate(roi, template, cv2.TM_CCOEFF_NORMED)[:,0]
    k = int(np.argmax(result)); score = float(result[k]); frac = 0.
    if 0 < k < len(result)-1:
        den = result[k-1]-2*result[k]+result[k+1]
        if abs(den) > 1e-9: frac = float(.5*(result[k-1]-result[k+1])/den)
    return score, lo+k+float(np.clip(frac,-.5,.5))

def clipped_match(field, template, lo, hi):
    score,y=y_match(field,template,lo,hi)
    if score >= .86: return score,y
    # A source label can cross behind browser chrome. Match only the visible
    # glyph rows rather than allowing a stale PROGRAMS word for those frames.
    # Require substantial visible ink and a stricter correlation for clips.
    best=(score,y)
    h=template.shape[0]
    for clip in range(1,h-2):
        for part,region,position in [
            (template[clip:],field[lo:lo+h-clip],lo-clip),
            (template[:-clip],field[hi-h+clip:hi],hi-h+clip),
        ]:
            if part.shape != region.shape or np.count_nonzero(part>.4)<40: continue
            corr=float(cv2.matchTemplate(region,part,cv2.TM_CCOEFF_NORMED)[0,0])
            if corr>.94 and corr>best[0]:best=(corr,float(position))
    return best

def fit_mask(mask, x, y, shape):
    # Fractional motion is applied to the replacement glyphs, not rounded between
    # frames. Rectangular edits are clipped to the current website viewport.
    return cv2.warpAffine(mask, np.array([[1,0,x],[0,1,y]],np.float32),
                          (shape[1],shape[0]), flags=cv2.INTER_LINEAR)

def ink(im, alpha, color):
    a = alpha[...,None]
    return im*(1-a)+np.array(color)[None,None,:]*a

def chrome_bounds(im, i):
    # The recording has two collapse sequences and two expansion sequences.
    # At transitions over the navy header the actual edge is measured in-frame.
    top = 162 if i <= 86 or 474 <= i <= 742 or i >= 842 else 72
    if 87 <= i <= 91 or 743 <= i <= 746 or 818 <= i <= 841:
        edge = im[72:163, :10].astype(float)
        colored = (edge.max(2)-edge.min(2)).mean(1) > 25
        matches = np.flatnonzero(colored)
        top = 72+int(matches[0]) if len(matches) else 162
    bottom = 1178 if i <= 86 or 474 <= i <= 742 or i >= 842 else 1298
    if 87 <= i <= 90:
        # Back-arrow displacement determines the translated toolbar's top edge.
        # Last frame's arrow is partly clipped; source-tracked positions are
        # 1213,1240,1256,1270 versus the expanded position 1194.
        bottom = [1197,1224,1240,1254][i-87]
    if 743 <= i <= 746 or 818 <= i <= 841:
        # The full-height menu provides an exact color boundary even before the
        # toolbar's icons become visible (no interpolated empty rectangles).
        edge = im[1150:, :10].astype(float)
        colored = (edge.max(2)-edge.min(2)).mean(1) > 25
        matches = np.flatnonzero(colored)
        bottom = 1151+int(matches[-1]) if len(matches) else 1298
    return int(top), int(bottom)

def normalize_chrome(im, top, bottom):
    out = im.copy()
    # Invert monochrome chrome only. Min-channel inversion additionally makes
    # the source yellow battery white rather than turning it blue/dark gray.
    for a,b in [(0,top),(bottom,H)]:
        lum = 255-im[a:b].min(2)
        out[a:b] = lum[...,None]
    # Remove the source's red recording/time pill. The reference hardware frame
    # supplies the replacement white clock, leaving minimal black margin.
    out[4:63, 34:165] = 0
    return out

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path)
parser.add_argument('--output-dir',type=Path,default=Path('/tmp/ww-naming'))
args=parser.parse_args(); outdir=args.output_dir; outdir.mkdir(parents=True,exist_ok=True)
FONT=outdir/'source-sans-pro.ttf'; woff=outdir/'source-sans-pro.woff2'
if not FONT.exists():
    subprocess.run(['curl','--fail','-Ls',FONT_URL,'-o',str(woff)],check=True)
    from fontTools.ttLib import TTFont
    font=TTFont(woff);font.flavor=None;font.save(FONT)
working=outdir/'source-30fps.mkv'
if not working.exists():
    subprocess.run(['ffmpeg','-v','error','-i',str(args.source),'-vf',
                    f'fps={FPS},scale={W}:{H}', '-an','-c:v','ffv1','-y',str(working)],check=True)
cap=cv2.VideoCapture(str(working)); refs={t:grab(cap,t) for t in [8,14.5,21,23,25]}
# Directly reuse the recording's Windsor Roman COURSES glyphs, at their source
# size. Only their foreground color is changed to the card's original purple.
course=refs[8][662:714].astype(float)
course_alpha=np.clip((255-course[...,1])/255,0,1).astype(np.float32)
course_alpha[course_alpha<.015]=0
source_purple=refs[14.5][660:709,65:530]
p=purple(source_purple)>0.9
purple_rgb=np.median(source_purple[p & (source_purple[...,1]<15)],axis=0)
anchor=purple(refs[14.5])[518:574,14:600]
# Template coordinates are measured once from the source, then independently
# matched every frame; menu expansion, scroll, clipping and hover colors remain
# properties of the source recording, not hand-keyed animated rectangles.
specs=[
 dict(name='adult-nav',ref=23,x0=35,x1=250,y0=345,y1=374,word_x=115,word_end=250,arrow=(262,283),new='COURSES',word_dy=5),
 dict(name='youth-nav',ref=23,x0=35,x1=258,y0=948,y1=977,word_x=124,word_end=258,arrow=(270,291),new='COURSES',word_dy=5),
 dict(name='adult-all',ref=23,x0=47,x1=263,y0=431,y1=461,word_x=149,word_end=263,arrow=None,new='Courses',word_dy=5),
 dict(name='youth-all',ref=25,x0=47,x1=270,y0=831,y1=862,word_x=156,word_end=270,arrow=None,new='Courses',word_dy=6),
]
for s in specs:
    r=refs[s['ref']].astype(float)
    s['template']=((r[s['y0']:s['y1'],s['x0']:s['x1'],1]-34)/221).astype(np.float32)
    s['glyph']=glyph(s['new'],27.6923077,150)
# Shortened words are ~22 CSS-scaled pixels narrower. Inline source arrows are
# shifted by this measured advance; all other menu pixels remain unchanged.
font16=ImageFont.truetype(str(FONT),round(27.6923077*16))
advance=(font16.getlength('PROGRAMS')-font16.getlength('COURSES'))/16
writers={}
for name in ['original','proposed']:
    path=outdir/f'ww-naming-{name}.mkv'
    writers[name]=subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24',
        '-s',f'{W}x{H}','-r',str(FPS),'-i','-','-an','-c:v','ffv1','-level','3','-y',str(path)],stdin=subprocess.PIPE)
cap.set(cv2.CAP_PROP_POS_FRAMES,0); tracks=[]; samples={0,402,405,408,414,420,435,465,473,474,626,627,628,629,630,642,660,690,720,744,745,750,757,758,780,791,792,810,825,830,840,867}
while True:
    ok,bgr=cap.read()
    if not ok: break
    i=len(tracks); im=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)
    top,bottom=chrome_bounds(im,i); original=normalize_chrome(im,top,bottom)
    proposed=original.astype(np.float32); rec={'frame':i,'top':top,'bottom':bottom,'edits':[]}
    if 12.8*FPS <= i <= 16.2*FPS:
        mask=purple(im)
        score,y=y_match(mask[:,14:600],anchor,top,H)
        # Source PROGRAMS begins 141 px beneath the source anchor's crop top.
        # The recorded word's first cap row is y659 (anchor top518).
        py=y+141
        if score>.86 and py<bottom and py+52>top:
            y0=max(top,int(np.floor(py))-2);y1=min(bottom,int(np.ceil(py))+54)
            proposed[y0:y1,56:545]=255
            a=fit_mask(course_alpha,0,py,(H,W));a[:top]=0;a[bottom:]=0
            proposed=ink(proposed,a,purple_rgb)
            rec['edits'].append({'name':'homepage','score':round(score,4),'y':round(py,3)})
    if i >= 20*FPS:
        field=((im[...,1].astype(np.float32)-34)/221)
        # Chrome/photos cannot become candidates: source menu ink must sit on
        # the source navy background, including partial rows at viewport edges.
        for s in specs:
            template=s['template']; replacement=s['glyph']; scale=1.
            if 626 <= i <= 633 and s['arrow']:
                # The actual source menu opens with a scaleY animation. Measure
                # its container edge; scale replacement glyphs by the exact same
                # factor, so no original word flashes during the first 4 frames.
                distance=np.linalg.norm(im[:,5].astype(float)-BG,axis=1)
                edge=328+int(np.flatnonzero(distance[328:1000]>10)[0])
                scale=min(1.,(edge-328)/332)
                matrix=np.array([[1,0,0],[0,scale,0]],np.float32)
                template=cv2.warpAffine(template,matrix,
                    (template.shape[1],int(np.ceil(template.shape[0]*scale))))
                replacement=cv2.warpAffine(replacement,matrix,
                    (replacement.shape[1],int(np.ceil(replacement.shape[0]*scale))))
            score,y=clipped_match(field[:,s['x0']:s['x1']],template,top,bottom)
            label_bottom=bottom
            if i == 719 and s['name']=='youth-all':
                # In this one source frame the submenu's own slideDown box,
                # not the browser viewport, cuts through the first child's
                # glyphs. Measure its last visible ink row and match a prefix
                # of the full source template; clip new ink at the same row.
                rows=(im[1030:1070,s['x0']:s['x1'],1]>90).sum(1)
                visible=np.flatnonzero(rows)
                if len(visible):
                    label_bottom=1031+int(visible[-1])
                    for keep in range(12,template.shape[0]):
                        part=template[:keep]
                        region=field[label_bottom-keep:label_bottom,s['x0']:s['x1']]
                        corr=float(cv2.matchTemplate(region,part,cv2.TM_CCOEFF_NORMED)[0,0])
                        if corr>score:
                            score,y=corr,float(label_bottom-keep)
            if score<.86: continue
            # Source glyph color (white/mint and opacity) is derived for this
            # frame, preserving expanded-menu highlight and animation states.
            yi=round(y); height=template.shape[0]
            vislo=max(top,yi);vishi=min(label_bottom,yi+height)
            roi=im[vislo:vishi,s['x0']:s['x1']].astype(float)
            templ=template[vislo-yi:vishi-yi]
            active=templ>.85*float(template.max())
            if roi.shape[:2] != active.shape:continue
            fg=np.median(roi[active],axis=0)
            local_bg=np.median(im[max(top,yi-2):min(bottom,yi+32),5:24],axis=(0,1))
            y0=max(top,yi-1);y1=min(label_bottom,yi+height+1)
            # Wipe only the changed word, never the unchanged prefix or FAQs.
            proposed[y0:y1,s['word_x']-1:s['word_end']+1]=local_bg
            if s['arrow']:
                ax0,ax1=s['arrow']; proposed[y0:y1,ax0-1:ax1+1]=local_bg
                arrow=im[y0:y1,ax0:ax1].astype(float)
                aa=np.clip((arrow[...,1]-BG[1])/(max(fg[1],BG[1]+1)-BG[1]),0,1).astype(np.float32)
                full=fit_mask(aa,ax0-advance,y0,(H,W));full[:top]=0;full[bottom:]=0
                proposed=ink(proposed,full,fg)
            a=fit_mask(replacement,s['word_x'],y+s['word_dy']*scale,(H,W));a[:top]=0;a[label_bottom:]=0
            proposed=ink(proposed,a,fg)
            rec['edits'].append({'name':s['name'],'score':round(score,4),'y':round(y,3),'scale_y':round(scale,5),
                                 **({'reveal_clip_bottom':label_bottom} if label_bottom!=bottom else {})})
    proposed=np.clip(np.rint(proposed),0,255).astype(np.uint8)
    writers['original'].stdin.write(original.tobytes());writers['proposed'].stdin.write(proposed.tobytes())
    if i in samples:
        Image.fromarray(original).save(outdir/f'original-{i:04}.png')
        Image.fromarray(proposed).save(outdir/f'proposed-{i:04}.png')
    tracks.append(rec)
for proc in writers.values():proc.stdin.close()
for proc in writers.values():assert proc.wait()==0
cap.release()
report={
 'purpose':'Proposed visual terminology mockup; not live implementation, user testing, or measured outcomes.',
 'source':{'filename':args.source.name,'sha256':sha(args.source),'duration_seconds':28.921667,'source_frames':1155,'vfr':True},
 'output':{'width':W,'height':H,'fps':FPS,'frames':len(tracks),'duration_seconds':len(tracks)/FPS,'audio':False,'start_seconds':0,
           'timing':'ffmpeg fps=30 samples the complete source at original speed; last frame padded by <1 frame to CFR; both outputs identical.'},
 'changes':MAPPING,'untouched_text':['FAQ – Adult Courses','FAQs – Youth Courses'],
 'browser_chrome':{'background':'#000000','icons_and_address':'white, source luminance antialiasing retained','status_height_px':72,
   'expanded_top_chrome_height_px':162,'expanded_bottom_toolbar_start_px':1178,
   'method':'In-frame source chrome boundaries; min-channel monochrome inversion only within chrome; recording pill removed under reference clock overlay.',
   'website_header':'Preserved source navy, not recolored.'},
 'font':{'family':'Source Sans Pro','source_url':FONT_URL,'woff2_sha256':sha(woff),'converted_ttf_sha256':sha(FONT),'size_output_px':27.6923077},
 'heading_glyphs':{'source_frame':240,'source_rect':[0,662,600,52],'method':'Source COURSES pixels/alpha reused at unchanged size; recolored to original card purple.'},
 'script':Path(__file__).name,'outputs':{},'tracking':tracks,
}
for name in writers:
 path=outdir/f'ww-naming-{name}.mkv';report['outputs'][name]={'file':path.name,'bytes':path.stat().st_size,'sha256':sha(path)}
json.dump(report,open(outdir/'provenance.json','w'),indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='tracking'},indent=2))
