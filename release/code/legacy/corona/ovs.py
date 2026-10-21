from PIL import Image; Image.MAX_IMAGE_PIXELS=None
import sys,os
for d in sys.argv[1:]:
  for p in 'abcd':
    f=f'{d}/{d}_{p}.tif'; im=Image.open(f); print(f,im.size); im.reduce(8).save(f'{d}/ov8_{p}.png')
