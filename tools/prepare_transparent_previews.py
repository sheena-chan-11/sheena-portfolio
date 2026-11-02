"""Optional reproducibility helper. Requires Pillow 13.0.0; run from any directory."""
from PIL import Image
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]; assets=root/'public/assets'
names=['program','competitor']; originals={n:Image.open(assets/f'ww-{n}-preview.png').convert('RGB') for n in names}
annotation_rows={'program':[(147,151),(684,688)],'competitor':[(255,259),(792,796)]}
crop=(46,1,486,904)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def is_annotation(name,y):return any(a<=y<b for a,b in annotation_rows[name])
def build(name):
 src=originals[name]; alt=originals[names[1-names.index(name)]]; out=src.convert('RGBA'); spans={}; changed_boundary=0
 # Construct silhouette without relying on the screen content, white highlights,
 # or turquoise annotation that crosses the source hardware.
 for y in range(src.height):
  clean=alt if is_annotation(name,y) else src
  core=[x for x in range(46,486) if min(clean.getpixel((x,y)))<220]
  if core:spans[y]=(core[0],core[-1],clean)
 for y in range(src.height):
  if y not in spans:
   # The one faint antialiased row below the phone has no dark core.
   # Keep only its neutral, nonwhite exterior using the last hardware row.
   nearby=min(spans,key=lambda yy:abs(yy-y)); left,right,clean=spans[nearby]
   for x in range(src.width):
    rgb=src.getpixel((x,y)); shade=min(rgb)
    if left<=x<=right and shade<255 and max(rgb)-min(rgb)<3:
     fg=originals[name].getpixel((x,nearby)); f=round(sum(fg)/3)
     alpha=round(255*(255-shade)/max(1,255-f))
     out.putpixel((x,y),(*fg,max(0,min(255,alpha))))
    else:out.putpixel((x,y),(0,0,0,0))
   continue
  left,right,clean=spans[y]
  for x in range(src.width):
   if left<=x<=right:continue
   if x<46 or x>=486:
    out.putpixel((x,y),(0,0,0,0));continue
   edge=left if x<left else right; fg=clean.getpixel((edge,y)); rgb=clean.getpixel((x,y))
   # All exterior pixels are neutral gray. Recover coverage by assuming the
   # nearest opaque hardware-edge gray is the foreground; unmatte against white.
   f=round(sum(fg)/3); shade=round(sum(rgb)/3)
   alpha=max(0,min(255,round(255*(255-shade)/max(1,255-f))))
   color=src.getpixel((x,y)) if is_annotation(name,y) else fg
   out.putpixel((x,y),(*color,alpha))
   if alpha:changed_boundary+=1
 result=out.crop(crop);path=assets/f'ww-{name}-preview-transparent.png';result.save(path,optimize=True)
 # Keep two light/dark backgrounds available for visual inspection, not shipped.
 for label,bg in [('lavender','#faf9fd'),('dark','#393445')]:
  composite=Image.new('RGBA',result.size,bg);composite.alpha_composite(result);composite.convert('RGB').save(f'/tmp/ww-{name}-transparent-{label}.png')
 retained=unchanged=0; white_count=0
 for y,(left,right,clean) in spans.items():
  for x in range(left,right+1):
   retained+=1;unchanged+=out.getpixel((x,y))==(*src.getpixel((x,y)),255)
   white_count+=src.getpixel((x,y))==(255,255,255)
 assert retained==unchanged
 assert result.mode=='RGBA' and all(result.getpixel(p)[3]==0 for p in [(0,0),(439,0),(0,902),(439,902)])
 extrema=result.getchannel('A').getextrema();assert extrema==(0,255)
 return {'source':f'public/assets/ww-{name}-preview.png','source_sha256':sha(assets/f'ww-{name}-preview.png'),'output':f'public/assets/ww-{name}-preview-transparent.png','output_sha256':sha(path),'source_dimensions':[530,905],'output_dimensions':list(result.size),'output_mode':result.mode,'crop_source_half_open':list(crop),'nontransparent_bbox_output_half_open':list(result.getbbox()),'nontransparent_bbox_source_half_open':[result.getbbox()[0]+46,result.getbbox()[1]+1,result.getbbox()[2]+46,result.getbbox()[3]+1],'annotation_source_y_half_open':annotation_rows[name],'checks':{'all_four_corner_alpha':0,'alpha_extrema':list(extrema),'enclosed_pixels_retained_exactly':retained,'enclosed_original_pure_white_pixels_retained_opaque':white_count,'partially_transparent_pixel_count':sum(0<a<255 for a in result.getchannel('A').getdata()),'antialiased_exterior_pixels':changed_boundary,'original_source_unchanged':True}}
outputs=[build(n) for n in names]
provenance={'purpose':'Transparent exterior-only derivatives of the two original annotated mobile preview screenshots. Original reference PNGs are intentionally untouched.','method':{'software':'Python 3.12 with Pillow 13.0.0','silhouette':'For each source y, first and last pixel with minimum RGB component <220 within hardware x range [46,486) define the fully opaque interval; every enclosed RGB pixel is copied unchanged. Exterior annotation rectangles are excluded from silhouette detection. No global white-key operation or replacement is applied to the website/browser UI.','annotation_crossings':'On each screenshot\u2019s four-pixel turquoise horizontal rules, derive the silhouette and edge coverage from the other original screenshot at the same y, where its hardware is unannotated. Preserve the current screenshot\u2019s original turquoise pixels inside the silhouette. Remove the rectangle\u2019s exterior segments along with the white background.','edge_antialias':'Outside each opaque interval, use the nearest core hardware edge RGB as foreground. Alpha = clamp(round(255 * (255 - mean(exterior RGB)) / (255 - mean(edge RGB))),0,255), with white matte 255. For neutral unannotated edges, save that edge RGB and recovered alpha; for turquoise crossing rows, retain the current source RGB under the same recovered alpha. Fully white exterior becomes alpha zero.','faint_bottom_edge':'Source y902 contains only faint neutral gray matte antialias. Recover alpha against the matching source x at nearest hardware-core row y901, restricted to its opaque interval. All other no-core rows become transparent.','crop':'Source half-open rectangle [46,1,486,904] = 440x903. Matches the existing extracted phone frame footprint, removes lateral white margins without resampling, and retains transparent padding at top/bottom.','interior_integrity':'No blur, resampling, screen erasure, screenshot replacement, UI recoloring, rim interpolation, or hardware repainting. All pixels from the row\u2019s first through last core edge retain the exact original RGB with alpha 255.'},'caveats':['The original screenshots were flattened on white, so true subpixel foreground colors/coverage cannot be uniquely recovered. Only exterior fringe pixels use the documented nearest-edge foreground estimate; enclosed hardware and all screenshot pixels remain exact.','The original turquoise annotations are intentionally retained inside the physical phone, including their existing crossings over hardware. Only the portions outside the silhouette disappear.','Derivative crop dimensions differ from original 530x905. Source and output coordinate geometry are documented per asset.'],'assets':outputs}
(root/'content/sources/womens-wilderness-transparent-previews.json').write_text(json.dumps(provenance,indent=2)+'\n')
print(json.dumps(outputs,indent=2))
