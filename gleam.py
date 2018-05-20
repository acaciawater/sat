'''
Created on May 15, 2018

@author: theo
'''
import os, re, datetime, gdal, osr
import netCDF4 as nc
import numpy as np
from sat import Base
from datetime import timedelta
from paramiko.client import SSHClient, AutoAddPolicy

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
DAY0 = datetime.date(1970,1,1)

GLEAM_HOST = 'hydras.ugent.be'
GLEAM_PORT = 2225
GLEAM_PATH = '/data/{version}/{year}'
GLEAM_VERSION = 'v3.2b'
GLEAM_USERNAME = 'gleamuser'
GLEAM_PASSWORD = 'hi_GLEAMv32#HiL?'
#sftp://hydras.ugent.be:2225/data/v3.2b/2003

class GLEAM(Base):

    def __init__(self, filename = None):
        Base.__init__(self,filename)
        # set default spatial reference
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        self.srs = sr.ExportToWkt()
        self.doy = 0 # day of the year to retrieve
        self.ssh = None
        
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
            # no bounding box: return entire tile
            data = ds[self.doy]
        else:
            # clip bounding box
            x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=True)
            data = ds[self.doy,int(x1):int(x2),int(y1):int(y2)]
        # need to transpose data for gdal: y is first index     
        return np.transpose(data)
    
    def iter_data(self,ds,bbox = None):
        ''' yield a tile for every day in this dataset ''' 
        if isinstance(ds,str):
            ds = self.get_dataset(ds)
        times = self.nc.variables['time']
        self.doy = 0
        for time in times:
            date = DAY0 + timedelta(days = int(time)) 
            yield (date, self.get_data(ds, bbox))
            self.doy += 1

    def connect(self, host, port=0, timeout=-999):
        if self.ssh is None:
            self.ssh = SSHClient() 
        self.ssh.set_missing_host_key_policy(AutoAddPolicy())
        self.ssh.connect(hostname=host,port=port,username=GLEAM_USERNAME,password=GLEAM_PASSWORD)
        self.ftp = self.ssh.open_sftp()
        return self.ftp

    def download(self, filename, folder, overwrite=True):
        print (filename)
        localpath = os.path.join(folder,filename)
        if not os.path.exists(folder):
            os.makedirs(folder)
        if os.path.exists(localpath):
            if not overwrite:
                print (localpath + ' exists')
                return
        self.ftp.get(filename,localpath)

    def download_tile(self, folder, tile, dest, overwrite = True):
        self.ftp.chdir(folder)
        files = self.ftp.listdir()
        for filename in files:
            if tile is None or tile in filename:
                self.download(filename, dest, overwrite)
                break

    def download_dataset(self, name, years, version, dest, overwrite=True):
        if self.ssh is None:
            self.connect(GLEAM_HOST,GLEAM_PORT)
        if not dest.endswith('/'):
            dest += '/'
        for year in years:
            folder = GLEAM_PATH.format(version=version,year=year)
            self.download_tile(folder, name, dest, overwrite)

    def create_tif(self, filename, extent, data, template, etype):

        if os.path.exists(filename):
            os.remove(filename)
        else:
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        ysize,xsize = data.shape
        tif = gdal.GetDriverByName('GTiff').Create(filename, xsize, ysize, eType=etype)
        tif.SetProjection(self.srs)
        tif.SetGeoTransform([extent[0],SIZE,0,extent[3],0,-SIZE])
        band = tif.GetRasterBand(1)
        band.WriteArray(data)

DESTFOLDER=r'/media/sf_Documents/projdirs/Ethiopia Unicef/gleam'
TESTFILE=r'/media/sf_Documents/projdirs/Ethiopia Unicef/gleam/SMroot_2017_GLEAM_v3.2b.nc'
#EXTENT=(-180,-90,180,90)
EXTENT=(33,3,48,15) # Ethiopia
DATASET=r'SMroot'

if __name__ == '__main__':
    
    gleam = GLEAM()
    os.chdir(DESTFOLDER) 
    gleam.download_dataset('SMroot', range(2003,2017), 'v3.2b', DESTFOLDER, overwrite=True)

#     if not gleam.open(TESTFILE):
#         print 'ERROR: cant open file', TESTFILE
#     else:
#         ds = gleam.get_dataset(DATASET)
#         if ds is None:
#             print 'ERROR: cant open dataset', DATASET
#         else:
#             for date,tile in gleam.iter_data(ds,EXTENT):
#                 filename = r'/media/sf_Documents/projdirs/Ethiopia Unicef/gleam/SMroot_{:%Y%m%d}_GLEAM_v3.2b.tif'.format(date)
#                 print filename
#                 gleam.create_tif(filename, EXTENT, tile, ds, etype=gdal.GDT_Float32)
                