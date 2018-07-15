import os, re, datetime, osr, gdal
import numpy as np
from sat import Base

class GPM(Base):
    ''' processes GPM netCDF4 files '''

    def __init__(self, filename = None):
        Base.__init__(self,filename)
        # set default spatial reference
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        self.wgs84 = sr.ExportToWkt()
    
    def extractdate(self,name):
        ''' extract date from filename'''
        #3B-DAY.MS.MRG.3IMERG.20140312-S000000-E235959.V05.nc4
        pat = r'3B\-DAY\.MS\.MRG\.3IMERG\.(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\-S000000\-E235959\.V05\.nc4$'
        m = re.search(pat, name)
        if m is None:
            # try version 5B, monthly
            # 3B-MO.MS.MRG.3IMERG.20171201-S000000-E235959.12.V05B.nc
            pat = r'3B\-MO\.MS\.MRG\.3IMERG\.(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\-S000000\-E235959\.(?P<month2>\d{2})\.V05B\.nc4$'
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
            ds.SetGeoTransform([-180,0.1,0,-90,0,0.1])

        return ds
   
    def get_data(self,ds,bbox=None):

        if isinstance(ds,str):
            ds = self.get_dataset(ds)

        band = ds.GetRasterBand(1)
        
        # transpose data
        data = band.ReadAsArray()
        
        if bbox:
            x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=False)
    
            xoff = int(x1)
            xsize = int(x2-x1)+1
            yoff = int(y1)
            ysize = int(y2-y1)+1
            data = data[yoff:yoff+ysize, xoff:xoff+xsize]
    
        data[data<-9998] = np.NaN
        return np.fliplr(np.transpose(data))
    
    def get_geotransform(self, dataset, extent=None):
        ''' get the geotransform of a dataset for a given extent '''
        trans = list(dataset.GetGeoTransform())
        if extent is None:
            trans[0] = -180.0
            trans[3] = -90.0
        else:
            trans[0] = extent[0]
            trans[3] = extent[1]
        return trans

    def convert_tif(self, dataset, folder, extent):
        for path, dirs, files in os.walk(folder):
            files.sort()
            for fil in files:
                if not self.is_datafile(fil):
                    continue
                print(fil)
                filename = fil.replace('hdf', dataset+'.tif')
                self.open(os.path.join(path,fil))
                ds = self.get_dataset(dataset)
                data = self.get_data(ds, extent) # 2-dimensional np.ndarray
                self.create_tif(os.path.join(path,filename), extent, data, ds, gdal.GDT_Float32)
                
# #TESTFILE=r'/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/GPM/3B-DAY.MS.MRG.3IMERG.20160820-S000000-E235959.V05.nc4'
# TESTFILE=r'/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/GPM/3B-DAY.MS.MRG.3IMERG.20170120-S000000-E235959.V05.nc4'
# FOLDER=r'/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/GPM'
# EXTENT=(-180,-90,180,90)
# DATASET=r'HQprecipitation'

# EXTENT=(33,3,48,15) # Ethiopia

# SRC = FOLDER
# DEST = FOLDER+'/stat'
# TILE = None

# if __name__ == '__main__':
    
#     gpm = GPM()
#     if not gpm.open(TESTFILE):
#         print ('ERROR: cant open file' + TESTFILE)
#     else:
#         ds = gpm.get_dataset(DATASET)
#         if ds is None:
#             print ('ERROR: cant open dataset' + DATASET)
#         else:
#             gpm.get_stat('HQprecipitation', SRC, DEST, TILE, EXTENT)
#             data = gpm.get_data(ds)
#             tif = gpm.create_tif(r'/media/sf_Documents/projdirs/Ethiopia Unicef/precipitation/GPM/gpm20170120.tif', EXTENT, data, ds, etype=gdal.GDT_Float32)
#             #tif.GetRasterBand(1).SetNoDataValue(-9999.0)

# #     gpm.convert_tif(DATASET, FOLDER, EXTENT)