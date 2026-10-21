# usage: locate.py <site_dir> <frame_id>  -> coarse location of the site centre in the scan pieces (S2 template vs 1/16 thumbnails)
import sys,glob,json,numpy as np,cv2,rasterio
site,fid=sys.argv[1],sys.argv[2]
m=json.load(open(f'{site}/raw/sentinel/s2_meta.json')); s=rasterio.open(m['file'])
rgb=s.read([3,2,1]).mean(0); n=rgb.shape[0]
cl=cv2.createCLAHE(2,(8,8))
def prep(z,valid=None):
    z=np.clip(z/np.percentile(z[z>0],99.5)*255,0,255).astype('uint8'); z=cl.apply(z).astype(np.float32)
    return cv2.GaussianBlur(z,(0,0),1.2)
c0=n//2; half=int(4000/10)   # central 8 km
tpl10=rgb[c0-half:c0+half,c0-half:c0+half]
res=[]
for f in sorted(glob.glob(f'{site}/corona/{fid}/{fid}_?.tif')):
    r=rasterio.open(f); th=r.read(1,out_shape=(r.height//16,r.width//16)).astype(np.float32)
    for rot in (0,180):
        I=th if rot==0 else cv2.rotate(th,cv2.ROTATE_180); Ip=prep(I)
        for gsd in np.arange(float(sys.argv[3]) if len(sys.argv)>3 else 1.5,float(sys.argv[4]) if len(sys.argv)>4 else 8,0.25):    # scan m/px
            px=16*gsd; t=cv2.resize(tpl10,None,fx=10/px,fy=10/px,interpolation=cv2.INTER_AREA)
            if t.shape[0]>=I.shape[0]-4 or t.shape[0]<40: continue
            tp=prep(t)
            for ang in (-8,-4,0,4,8):
                M=cv2.getRotationMatrix2D((tp.shape[1]/2,tp.shape[0]/2),ang,1); tt=cv2.warpAffine(tp,M,tp.shape[::-1]); k=int(tt.shape[0]*.15); tt=tt[k:-k,k:-k]
                rr=cv2.matchTemplate(Ip,tt,cv2.TM_CCOEFF_NORMED); _,mx,_,loc=cv2.minMaxLoc(rr)
                res.append((float(mx),f,rot,float(gsd),ang,loc,tt.shape[0]))
res.sort(key=lambda x:-x[0])
for x in res[:8]: print(x)
b=res[0]; json.dump(dict(zip(['ncc','file','rot','gsd','ang','loc','size'],b)),open(f'{site}/corona/{fid}_locate.json','w'))
