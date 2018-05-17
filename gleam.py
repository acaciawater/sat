'''
Created on May 15, 2018

@author: theo
'''
import os, re, datetime, gdal, osr
import netCDF4 as nc
import numpy as np
from sat import Base

# TODO: use NETCDF interface directly
# 3D array 720x1440xndays
# cell (0,0) is centered around lat=89.875 and lon=-179.875
# cell sizes: 0.25 degree
# ds =nc.Dataset('SMroot_2017_GLEAM_v3.2b.nc')
# sm = ds.variables['SMroot')
# pixel = sm[time,lon,lat]
# tile = sm[time,:,:]
# series = sm[:,lon,lat]

LEFT = -180
TOP = 90
SIZE = 0.25
WIDTH = 1440
HEIGHT = 720

class GLEAM(Base):

    def __init__(self, filename = None):
        Base.__init__(self,filename)
        # set default spatial reference
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        self.srs = sr.ExportToWkt()
    
    def open(self, filename):
        self.nc = nc.Dataset(filename)
        return self.nc is not None

    def close(self):
        self.nc = None

    def getcolrow(self,ds,lon,lat):
        col = (lon - LEFT) / SIZE
        row = (TOP - lat) / SIZE
        return (col,row)

    def extractdate(self,name):
        ''' extract year from filename'''
        #SMroot_2017_GLEAM_v3.2b.nc
        pat = r'(?P<var>\w+)_(?P<year>\d{4})_GLEAM_v(?P<ver>\d\.\d\w)\.nc$'
        m = re.search(pat, name)
        if m is not None:
            year = int(m.group('year'))
            return datetime.date(year,1,1)
        return None
        
    def get_dataset(self, name):
        return self.nc.variables[name]

    def transbox(self, ds, bbox, topix=False, clip=False):

        x1,y1,x2,y2 = bbox

        if clip or topix:

            px1,py1 = self.getcolrow(ds,x1,y1)
            px2,py2 = self.getcolrow(ds,x2,y2)
            
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

    
    def get_data(self,ds,bbox=None):

        if isinstance(ds,str):
            ds = self.get_dataset(ds)

        if bbox is None:
            return ds[0]

        x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=True)

        xoff = int(x1)
        xsize = int(x2-x1)
        yoff = int(y1)
        ysize = int(y2-y1)

        # gets data for all time steps in this file (all days in current year)
        data = ds[0, yoff:yoff+ysize, xoff:xoff+xsize]
        
        return data
    
    def create_tif(self, filename, extent, data, template, etype):

        if os.path.exists(filename):
            os.remove(filename)
        else:
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        print filename
        ysize,xsize = data.shape
        tif = gdal.GetDriverByName('GTiff').Create(filename, xsize, ysize, eType=etype)
        tif.SetProjection(self.srs)
        tif.SetGeoTransform([extent[0],SIZE,0,extent[3],0,-SIZE])
        band = tif.GetRasterBand(1)
        band.WriteArray(data)

TESTFILE=r'/media/sf_Documents/projdirs/Ethiopia Unicef/gleam/SMroot_2017_GLEAM_v3.2b.nc'
EXTENT=(-180,-90,180,90)
DATASET=r'SMroot'

if __name__ == '__main__':
    
    gleam = GLEAM()
    if not gleam.open(TESTFILE):
        print 'ERROR: cant open file', TESTFILE
    else:
        ds = gleam.get_dataset(DATASET)
        if ds is None:
            print 'ERROR: cant open dataset', DATASET
        else:
            data = gleam.get_data(ds)
            #col,row = gleam.getcolrow(ds, 5.01,-1.81)
            #value0 = round(data[col][row],3)
            #assert value0==0.145, "Value={}, expected 0.145".format(value0)
            data = np.array(data,dtype=np.float64)
            data = np.transpose(data)
            gleam.create_tif(r'/media/sf_Documents/projdirs/Ethiopia Unicef/gleam/SMroot_2017_GLEAM_v3.2b.tif', EXTENT, data, ds, etype=gdal.GDT_Float64)