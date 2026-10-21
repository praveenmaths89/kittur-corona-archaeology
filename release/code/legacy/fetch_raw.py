"""Re-download all raw inputs by ID into raw/. Usage: python release/code/fetch_raw.py [corona|sentinel|landsat|dem|soi|gazetteer|all]
CORONA needs a free USGS EarthExplorer account: set M2M_USERNAME and M2M_TOKEN (application token, never a password in code)."""
import os,sys,json,subprocess,urllib.request
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); RAW=os.path.join(ROOT,'raw')
CORONA=['DS1045-1102DA224','DS1045-1102DF224','DS1045-1102DA223','DS1044-2134DA217','DS1044-2134DF217']  # dataset corona2
S2=['S2B_43PDT_20260217_0_L2A','S2B_43PDT_20260915_0_L2A','S2C_43PDT_20261010_0_L2A','S2B_43PDT_20261015_0_L2A']  # Earth Search sentinel-2-l2a
EPOCH_JSON=['L1990','L2000','L2010','S2016','S2020','S2026']  # item lists stored in raw/landsat|sentinel/*.json
DEM='https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N15_00_E074_00_DEM/Copernicus_DSM_COG_10_N15_00_E074_00_DEM.tif'
SOI_ZENODO='https://zenodo.org/api/records/18133392'
GAZ='https://archive.org/download/wbsl.17016'   # Gazetteer of the Bombay Presidency XXI Belgaum (1884), djvu.txt
def get(u,dst):
    os.makedirs(os.path.dirname(dst),exist_ok=True)
    if not os.path.exists(dst): print('GET',u); urllib.request.urlretrieve(u,dst)
def corona():
    api='https://m2m.cr.usgs.gov/api/api/json/stable/'
    def post(ep,d,key=None):
        r=urllib.request.Request(api+ep,json.dumps(d).encode(),{'Content-Type':'application/json',**({'X-Auth-Token':key} if key else {})})
        return json.load(urllib.request.urlopen(r))['data']
    key=post('login-token',{'username':os.environ['M2M_USERNAME'],'token':os.environ['M2M_TOKEN']})
    opts=post('download-options',{'datasetName':'corona2','entityIds':CORONA},key)
    dl=[{'entityId':o['entityId'],'productId':o['id']} for o in opts if o['available']]
    res=post('download-request',{'downloads':dl,'label':'kittur'},key)
    for d in res.get('availableDownloads',[]): get(d['url'],os.path.join(RAW,'corona',f"{d['entityId']}.tgz") if 'entityId' in d else os.path.join(RAW,'corona',os.path.basename(d['url'])))
def sentinel():
    subprocess.run([sys.executable,os.path.join(ROOT,'release/code/base/s2.py')]+[f"x{i}={s}" for i,s in enumerate(S2)],cwd=ROOT,check=True)
def dem(): get(DEM,os.path.join(RAW,'dem','Copernicus_DSM_COG_10_N15_00_E074_00_DEM.tif'))
def soi():
    rec=json.load(urllib.request.urlopen(SOI_ZENODO))
    for f in rec['files']:
        if any(s in f['key'] for s in ['48_I_09','48_I_10','48_I_13','48_I_14','48 I 09','48 I 10','48 I 13','48 I 14']): get(f['links']['self'],os.path.join(RAW,'soi',f['key']))
def gazetteer(): get(GAZ+'/'+'wbsl.17016_djvu.txt',os.path.join(RAW,'texts','belgaum1884_djvu.txt'))
def landsat(): subprocess.run([sys.executable,os.path.join(ROOT,'release/code/epochs/fetch.py')],cwd=os.path.join(ROOT,'epochs'),check=True)
if __name__=='__main__':
    w=sys.argv[1] if len(sys.argv)>1 else 'all'
    for f in ([dem,soi,gazetteer,sentinel,landsat,corona] if w=='all' else [globals()[w]]): f()
