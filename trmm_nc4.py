'''
Created on Jul 15, 2018

@author: theo
Process TRMM netCDF4 files using python's netcdf4 module
'''

import os, gdal, osr
import netCDF4 as nc
import numpy as np

TESTFILE = '/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/TRMM/3B42_Daily.19980101.7.nc4'
DATASET = 'precipitation'
OUTFILE = '/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/3B42_Daily.19980101.7.tif'

EXTENT = (-180,-50,180,50)
SIZE = 0.25

dataset = nc.Dataset(TESTFILE)
prec = dataset.variables[DATASET]
data = prec[:,:].T # dimensions are (lat,lon). Transpose for gdal  
data[data<0] = np.NaN # clear fill value (no need to set nodata)
if os.path.exists(OUTFILE):
    os.remove(OUTFILE)
else:
    dirname = os.path.dirname(OUTFILE)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
ysize,xsize = data.shape
tif = gdal.GetDriverByName('GTiff').Create(OUTFILE, xsize, ysize, eType=gdal.GDT_Float32)
sr = osr.SpatialReference()
sr.ImportFromEPSG(4326)
srs = sr.ExportToWkt()
tif.SetProjection(srs)
geotransform = (EXTENT[0],SIZE,0,EXTENT[1],0,SIZE)
tif.SetGeoTransform(geotransform)
band = tif.GetRasterBand(1)
band.WriteArray(data)



