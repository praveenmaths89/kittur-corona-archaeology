import cv2,numpy as np,rasterio,json,sys
from PIL import Image; Image.MAX_IMAGE_PIXELS=None
from rasterio.warp import transform
from rasterio.windows import from_bounds
big=Image.open('DS1045-1102DA224_b.tif')
M=np.load('M_b.npy'); Mi=np.linalg.inv(np.vstack([M,[0,0,1]]))
s2=rasterio.open('../qgis/rasters/s2_dry_20260217_truecolour.tif')
sift=cv2.SIFT_create(20000); cl=cv2.createCLAHE(2,(8,8))
sites={'kittur':(15.6004,74.7911),'sangolli':(15.7171,74.8337),'nandagad':(15.5789,74.5737)}
res={}
for n,(la,lo) in sites.items():
    x,y=transform('EPSG:4326','EPSG:32643',[lo],[la]); x,y=x[0],y[0]
    H=4000  # m half-size search
    w=from_bounds(x-H,y-H,x+H,y+H,s2.transform)
    a=s2.read(window=w,boundless=True).astype(float).mean(0)
    st=s2.window_transform(w)
    a=cl.apply(np.clip(a/np.percentile(a,99)*255,0,255).astype('uint8'))
    px=(x-440990)/30; py=(1757960-y)/30; c=(Mi@[px,py,1])[:2]*16
    R=2600  # full-res px half (~2.2m -> ~5.7km)
    box=(int(c[0]-R),int(max(0,c[1]-R)),int(c[0]+R),int(min(10032,c[1]+R)))
    cr=np.array(big.crop(box))
    f=4.5; sm=cv2.resize(cr,None,fx=1/f,fy=1/f,interpolation=cv2.INTER_AREA)
    sm=cl.apply(sm)
    k1,d1=sift.detectAndCompute(sm,None); k2,d2=sift.detectAndCompute(a,None)
    m=cv2.BFMatcher().knnMatch(d1,d2,k=2); g=[p for p,q in m if p.distance<0.85*q.distance]
    A=np.float32([k1[i.queryIdx].pt for i in g]); B=np.float32([k2[i.trainIdx].pt for i in g])
    Ma,inl=cv2.estimateAffine2D(A,B,method=cv2.RANSAC,ransacReprojThreshold=4)
    inl=inl.ravel()==1
    print(n,box,len(g),inl.sum(),Ma.round(3).tolist())
    # GCPs: full-res pixel -> UTM
    P=A[inl]*f+[box[0],box[1]]
    E=np.array([st*(u,v) for u,v in B[inl]])
    res[n]=dict(box=box,P=P.tolist(),E=E.tolist())
    cv2.imwrite('dbg_%s_c.png'%n,sm); cv2.imwrite('dbg_%s_s.png'%n,a)
json.dump(res,open('gcps.json','w'))
