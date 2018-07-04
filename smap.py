import os, re, datetime, osr, gdal
import numpy as np
from sat import Base

class SMAP(Base):
    ''' processes SMAP/Sentinel-1 hdf5 files '''

    def __init__(self, filename = None):
        Base.__init__(self,filename)
        # set default spatial reference
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(6933) # EASE-2.0
        #sr.ImportFromEPSG(4326) # WGS84
        self.srs = sr.ExportToWkt()

    def extractdate(self,name):
        ''' extract date from filename'''
        #/media/sf_Documents/projdirs/Ethiopia Unicef/SMAP/SMAP_L2_SM_SP_1BIWDV_20180630T030744_20180629T152532_041E09N_R16010_001.h5
        pat = r'SMAP_L2_SM_SP_1BIWDV_(?P<end>\d{8}T\d{6})_(?P<start>\d{8}T\d{6})_(?P<lon>\d{3}[EW])(?P<lat>\d{2}[NS])_R[0-9_]+\.h5'
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
            self.set_projection(ds)
        return ds

    def get_lon_lat(self,ds):
        path = ds.GetDescription()
        if path.endswith('1km'):
            lon = self.get_data(Base.get_dataset(self, LON1K))
            lat = self.get_data(Base.get_dataset(self, LAT1K))
        elif path.endswith('3km'):
            lon = self.get_data(Base.get_dataset(self, LON3K))
            lat = self.get_data(Base.get_dataset(self, LAT3K))
        else:
            raise
        return (lon,lat)
    
    def set_projection(self, ds):
        lon,lat = self.get_lon_lat(ds)
        
        nrows, ncols = lon.shape
        left = float(np.min(lon))
        right = float(np.max(lon))
        top = float(np.max(lat))
        bot = float(np.min(lat))
        
        # reproject points
        sr1 = osr.SpatialReference()
        sr1.ImportFromEPSG(6933) # EASE-2.0
        ease2 = sr1.ExportToWkt()

        sr2 = osr.SpatialReference()
        sr2.ImportFromEPSG(4326) # WGS84
        wgs84 = sr2.ExportToWkt()
        
        trans = osr.CoordinateTransformation(sr2, sr1)
        xmin,ymin,zmin = trans.TransformPoint(left,bot)
        xmax,ymax,zmax = trans.TransformPoint(right,top)
        size = (xmax-xmin)/ncols
        if size < 1100:
            size = 1000
        else:
            size = 3000
        xmin -= size/2
        ymin -= size/2
        
        ds.SetGeoTransform((xmin,size,0,ymin,0,size))
        ds.SetProjection(ease2)

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
                
TESTFILE='/media/sf_Documents/projdirs/Ethiopia Unicef/SMAP/SMAP_L2_SM_SP_1BIWDV_20180630T030744_20180629T152532_041E09N_R16010_001.h5'
#TESTFILE = '/media/sf_Documents/projdirs/Ethiopia Unicef/SMAP/SMAP_L2_SM_SP_1BIWDV_20180628T033111_20180629T025927_042E11N_R16010_001.h5'
FOLDER=r'/media/sf_Documents/projdirs/Ethiopia Unicef/SMAP'
OUTFILE = FOLDER+'/DDSM1K.tif'
#EXTENT=(-180,-90,180,90)
EXTENT=None

SM3K=r'Soil_Moisture_Retrieval_Data_3km/soil_moisture_3km'
LON3K=r'Soil_Moisture_Retrieval_Data_3km/longitude_3km'
LAT3K=r'Soil_Moisture_Retrieval_Data_3km/latitude_3km'

SM1K=r'Soil_Moisture_Retrieval_Data_1km/soil_moisture_1km'
LON1K=r'Soil_Moisture_Retrieval_Data_1km/longitude_1km'
LAT1K=r'Soil_Moisture_Retrieval_Data_1km/latitude_1km'

DATASET = SM1K
LON = LON1K
LAT = LAT1K

if __name__ == '__main__':
    
    sm = SMAP()
    if not sm.open(TESTFILE):
        print ('ERROR: cant open file' + TESTFILE)
    else:
        ds = sm.get_dataset(SM1K)
        if ds is None:
            print ('ERROR: cant open dataset' + DATASET)
        else:
            data = sm.get_data(ds).T
            lon,lat = sm.get_lon_lat(ds)
 
            nrows, ncols = data.shape
            left = float(np.min(lon))
            right = float(np.max(lon))
            top = float(np.max(lat))
            bot = float(np.min(lat))
            
            # reproject points
            sr1 = osr.SpatialReference()
            sr1.ImportFromEPSG(6933) # EASE-2.0
            ease2 = sr1.ExportToWkt()
            sr2 = osr.SpatialReference()
            sr2.ImportFromEPSG(4326) # WGS84
            wgs84 = sr2.ExportToWkt()
            trans = osr.CoordinateTransformation(sr2, sr1)
            xmin,ymin,zmin = trans.TransformPoint(left,bot)
            xmax,ymax,zmax = trans.TransformPoint(right,top)
            size = (xmax-xmin)/ncols
            if size < 1100:
                size = 1000
            else:
                size = 3000
            xmin -= size/2
            ymin -= size/2
            
            tif = gdal.GetDriverByName('Gtiff').Create(OUTFILE,ncols, nrows, 1, gdal.GDT_Float32)
            tif.SetGeoTransform((xmin,size,0,ymin,0,size))
            tif.SetProjection(ease2)
            tif.GetRasterBand(1).WriteArray(data)
            #tif.GetRasterBand(1).SetNoDataValue(-9999.0)

#     gpm.convert_tif(DATASET, FOLDER, EXTENT)