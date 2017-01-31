'''
Created on Apr 28, 2016

@author: theo
'''
import os,re, sys
import gdal
import numpy as np
from scipy.stats import linregress

#SRC = r'/media/GONWKS2/GIS_bestanden/Africa/modis/ndvi/mod13c2.006'
PATTERN = r'NDVI\.all\.(?P<year>\d{4})\.mean\.tif'
SRC = r'/home/theo/src/sat'

def save(folder,name,data,template,eType=gdal.GDT_Float32):
    ysize,xsize = data.shape
    filename = os.path.join(folder, name+'.tif')
    if os.path.exists(filename):
        os.remove(filename)
    tif = gdal.GetDriverByName('GTiff').Create(filename, xsize, ysize, eType=eType)
    tif.SetProjection(template.GetProjection())
    tif.SetGeoTransform(template.GetGeoTransform())
    band = tif.GetRasterBand(1)
    band.WriteArray(data)
    tif = None
    
data = {}
template = None
for path, dirs, files in os.walk(SRC):
    for fil in files:
        m = re.search(PATTERN, fil)
        if m is not None:
            year = int(m.group('year'))
            dataset = os.path.join(path,fil)
            ds = gdal.OpenShared(dataset)
            if template is None:
                template = ds
            band = ds.GetRasterBand(1)
            data[year] = band.ReadAsArray()
# calculate trend
years = data.keys()
dim = data[years[0]].shape
height,width = dim
slope = np.ndarray(dim,dtype=np.float32)
correl = np.ndarray(dim,dtype=np.float32)
stderr = np.ndarray(dim,dtype=np.float32)
for i in range(height):
    sys.stderr.write('\r%d   ' % (height-i))
    for j in range(width):
        values = [data[y][i][j] for y in years]
        rc, intercept, rvalue, pvalue, evalue = linregress(years, values)
        slope[i][j] = rc
        correl[i][j] = rvalue
        stderr[i][j] = evalue

save(SRC,'NDVI.all.slope', slope, template)
save(SRC,'NDVI.all.correl', correl, template)
save(SRC,'NDVI.all.stderr', stderr, template)
