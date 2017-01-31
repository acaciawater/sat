'''
Created on Apr 29, 2016

@author: theo
'''
from arc2.arc2 import ARC2
from datetime import date
import numpy as np

#ARC2SRC = r'/media/GONWKS2/GIS_bestanden/Africa/arc2/bin'
ARC2SRC = r'/media/sf_F_DRIVE/projdirs/Afar/arc2/bin'
AFRICA = (-20, -36, 55, 38)
DEST = r'G:\GIS_bestanden\Africa\arc2\stat\arc2'
THRESHOLD = 3 # 3 mm/d theshold

#--------------------------------------------------------------

arc=ARC2()
tiles = arc.get_tiles(ARC2SRC,AFRICA,date(2013,1,1),date(2013,12,31))
years = set([d.year for d,t in tiles])

sums = []
for y in years:
    data = np.array([t for d,t in tiles if d.year == y])
    data = data > THRESHOLD
    if data.shape[0] > 364:
        sums.append(data.count(axis=0))

