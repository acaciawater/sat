'''
Created on Jul 15, 2018

@author: theo
Process GPM netCDF4 files using python's netcdf4 module
'''

import os
import gdal
import osr
import re
import datetime
import netCDF4 as nc
import numpy as np
from sat import Base

EXTENT = (-180,-50,180,50)
LEFT, BOTTOM, RIGHT, TOP = EXTENT
DIM = (1440,400)
WIDTH, HEIGHT = DIM
SIZE = 0.25

class TRMM(Base):

    def __init__(self, filename=None):
        # set default spatial reference
        
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        self.srs = sr.ExportToWkt()
        Base.__init__(self,filename)
    
    def GetProjection(self):
        # gdal dataset stub
        return self.srs
    
    def open(self, filename):
        self.hdf = nc.Dataset(filename)
        return self.hdf is not None

    def get_dataset(self, name):
        return self.hdf.variables[name]

    def getcolrow(self,lon,lat):
        col = (lon - LEFT) / SIZE
        row = (lat - BOTTOM) / SIZE
        return (col,row)

    def extractdate(self,name):
        ''' extract date from filename'''
        #3B42_Daily.20180328.7.nc4
        pat = r'3B42_Daily\.(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\.7\.nc4$'
        m = re.search(pat, name)
        if m is not None:
            year = int(m.group('year'))
            month = int(m.group('month'))
            day = int(m.group('day'))
            return datetime.date(year,month,day)
        return None

    def transbox(self, ds, bbox, topix=False, clip=False):

        x1,y1,x2,y2 = bbox

        if clip or topix:

            px1,py1 = self.getcolrow(x1,y1)
            px2,py2 = self.getcolrow(x2,y2)
            
            if clip:
                px1 = max(0,min(px1,WIDTH-1))
                px2 = max(0,min(px2,WIDTH-1))
                py1 = max(0,min(py1,HEIGHT-1))
                py2 = max(0,min(py2,HEIGHT-1))
            
            if topix:
                x1 = int(px1)
                x2 = int(px2)
                y1 = int(py1)
                y2 = int(py2)
                
        if y1 > y2:
            return (x1,y2,x2,y1)
        else:
            return (x1,y1,x2,y2)

    def get_geotransform(self, dataset, extent=None):
        ''' get the geotransform of a dataset for a given extent '''
        trans = [LEFT,SIZE,0,BOTTOM,0,SIZE]
        if extent is not None:
            trans[0] = extent[0]
            trans[3] = extent[1]
        return trans

    def get_data(self,ds,bbox=None):

        if isinstance(ds,str):
            ds = self.get_dataset(ds)

        if bbox is None:
            # no bounding box: return entire tile
            data = ds[:,:]
        else:
            # clip bounding box
            x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=True)
            data = ds[int(x1):int(x2),int(y1):int(y2)]
        # need to transpose data for gdal     
        return np.transpose(data)

    def create_tif(self, filename, extent, data, template, etype):

        if os.path.exists(filename):
            os.remove(filename)
        else:
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        ysize,xsize = data.shape
        tif = gdal.GetDriverByName('GTiff').Create(filename, xsize, ysize, eType=etype)
        self.copy_projection(self, tif, extent)
        band = tif.GetRasterBand(1)
        band.WriteArray(data)
        tif.FlushCache()
        tif = None
        
if __name__ == '__main__':

    # TESTFILE = '/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/TRMM/3B42_Daily.19980101.7.nc4'
    # OUTFILE = '/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/3B42_Daily.19980101.7.tif'
    # OUTFILE2 = '/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/3B42_Daily.ethiopia.tif'
    TESTFILE = r'C:\Users\theo\Documents\projdirs\Ethiopia Unicef\precipitation\TRMM\3B42_Daily.19980101.7.nc4'
    OUTFILE = r'C:\Users\theo\Documents\projdirs\Ethiopia Unicef\precipitation\3B42_Daily_19980101.tif'
    OUTFILE2 = r'C:\Users\theo\Documents\projdirs\Ethiopia Unicef\precipitation\3B42_Daily_ethiopia.tif'

    DATASET = 'precipitation'
    ETHIOPIA = (33,3,48,15)
 
    tr = TRMM(TESTFILE)
    data = tr.get_data(DATASET, bbox=ETHIOPIA)
    tr.create_tif(OUTFILE2, extent=ETHIOPIA, data=data, template=None, etype=gdal.GDT_Float32)
    
#     dataset = nc.Dataset(TESTFILE)
#     prec = dataset.variables[DATASET]
#     data = prec[:,:].T # dimensions are (lat,lon). Transpose for gdal  
#     data[data<0] = np.NaN # clear fill value (no need to set nodata)
#  
#     if os.path.exists(OUTFILE):
#         os.remove(OUTFILE)
#     else:
#         dirname = os.path.dirname(OUTFILE)
#         if not os.path.exists(dirname):
#             os.makedirs(dirname)
#     ysize,xsize = data.shape
#     tif = gdal.GetDriverByName('GTiff').Create(OUTFILE, xsize, ysize, eType=gdal.GDT_Float32)
#     sr = osr.SpatialReference()
#     sr.ImportFromEPSG(4326)
#     srs = sr.ExportToWkt()
#     tif.SetProjection(srs)
#     geotransform = (EXTENT[0],SIZE,0,EXTENT[1],0,SIZE)
#     tif.SetGeoTransform(geotransform)
#     band = tif.GetRasterBand(1)
#     band.WriteArray(data)
#     tif.FlushCache()
#     tif = None
