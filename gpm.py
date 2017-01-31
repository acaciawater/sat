'''
Created on Jan 6, 2016

@author: theo
'''
import os, re, datetime, osr, gdal
from sat import Base

class GPM(Base):

    def __init__(self, filename = None):
        Base.__init__(self,filename)
        # set default spatial reference
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        self.wgs84 = sr.ExportToWkt()
    
    def extractdate(self,name):
        ''' extract date from filename'''
        # 3B-DAY-L.MS.MRG.3IMERG.20161218-S000000-E235959.V03.nc4
        pat = r'3B\-DAY\-L\.MS\.MRG\.3IMERG\.(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\-S000000\-E235959\.V03\.hdf$'
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
            ds.SetGeoTransform([-180,0.1,0,-60,0,0.1])
            # transpose dimensions
            t = ds.RasterXSize
            ds.RasterXSize = ds.RasterYSize
            ds.RasterYSize = t

        return ds

    def get_data(self,ds,bbox=None):

        if isinstance(ds,str):
            ds = self.get_dataset(ds)

        band = ds.GetRasterBand(1)
        # transpose data
        data = band.ReadAsArray().T
        if bbox is None:
            return data

        x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=False)

        xoff = int(x1)
        xsize = int(x2-x1)+1
        yoff = int(y1)
        ysize = int(y2-y1)+1
        return data[yoff:yoff+ysize, xoff:xoff+xsize]

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
        tif.SetProjection(template.GetProjection())
        trans = list(template.GetGeoTransform())
        if extent is not None:
            trans[0] = extent[0]
            trans[3] = extent[1]
        tif.SetGeoTransform(trans)
        band = tif.GetRasterBand(1)
        band.WriteArray(data)
    
    def convert_tif(self, dataset, folder, extent):
        for path, dirs, files in os.walk(folder):
            files.sort()
            for fil in files:
                if not self.is_datafile(fil):
                    continue
                print fil
                filename = fil.replace('hdf', dataset+'.tif')
                self.open(os.path.join(path,fil))
                ds = self.get_dataset(dataset)
                data = self.get_data(ds, extent) # 2-dimensional np.ndarray
                self.create_tif(os.path.join(path,filename), extent, data, ds, gdal.GDT_Float32)
                
#TESTFILE=r'/media/sf_C_DRIVE/Users/theo/Documents/projdirs/hdf/3B-DAY-L.MS.MRG.3IMERG.20150314-S000000-E235959.V03.hdf'
#FOLDER=r'/media/sf_C_DRIVE/Users/theo/Documents/projdirs/hdf'
TESTFILE=r'/home/theo/src/sat/hdf/3B-DAY-L.MS.MRG.3IMERG.20150314-S000000-E235959.V03.hdf'
FOLDER=r'/home/theo/src/sat/hdf'
EXTENT=(10,10,50,50)
DATASET=r'HQprecipitation'
if __name__ == '__main__':
    
    gpm = GPM()
#     if not gpm.open(TESTFILE):
#         print 'ERROR: cant open file', TESTFILE
#     else:
#         ds = gpm.get_dataset(DATASET)
#         if ds is None:
#             print 'ERROR: cant open dataset', DATASET
#         else:
#             data = gpm.get_data(DATASET,EXTENT)
#             gpm.create_tif(r'/media/sf_C_DRIVE/Users/theo/Documents/projdirs/hdf/out7.tif', EXTENT, data, ds, etype=gdal.GDT_Float32)
    gpm.convert_tif(DATASET, FOLDER, EXTENT)