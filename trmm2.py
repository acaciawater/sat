import os, re, datetime, osr, gdal
import numpy as np
from .gpm2 import GPM
from .sat import Base

class TRMM(GPM):
    ''' processes TRMM netCDF4 files '''

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

    def get_dataset(self, name):
        ds = Base.get_dataset(self, name)
        if ds:
            if not ds.GetProjection():
                ds.SetProjection(self.wgs84)
            ds.SetGeoTransform([-180,0.25,0,-50,0,0.25])

        return ds

    def get_data(self,ds,bbox=None):

        if isinstance(ds,str):
            ds = self.get_dataset(ds)

        band = ds.GetRasterBand(1)
        
        data = band.ReadAsArray()
        data = np.fliplr(np.transpose(data))
        
        if bbox:
            x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=False)
    
            xoff = int(x1)
            xsize = int(x2-x1)+1
            yoff = int(y1)
            ysize = int(y2-y1)+1
            data = data[yoff:yoff+ysize,xoff:xoff+xsize]
    
        data[data<-9998] = np.NaN
        return data

    def get_geotransform(self, dataset, extent=None):
        ''' get the geotransform of a dataset for a given extent '''
        trans = list(dataset.GetGeoTransform())
        if extent is None:
            trans[0] = -180.0
            trans[3] = -50.0
        else:
            trans[0] = extent[0]
            trans[3] = extent[1]
        return trans
                    