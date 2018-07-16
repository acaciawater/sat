from trmm2 import TRMM
import gdal

TESTFILE=r'C:\Users\theo\Documents\projdirs\Ethiopia Unicef\precipitation\TRMM\3B42_Daily.19980101.7.nc4'
FOLDER=r'C:\Users\theo\Documents\projdirs\Ethiopia Unicef\precipitation\TRMM'
DATASET=r'precipitation'

EXTENT=(-180,-50,180,50)
#EXTENT=(33,3,48,15) # Ethiopia

SRC = FOLDER
DEST = FOLDER+'/stat'
TILE = None

if __name__ == '__main__':
    trmm = TRMM()
    if not trmm.open(TESTFILE):
        print ("ERROR: can't open file" + TESTFILE)
    else:
        ds = trmm.get_dataset(DATASET)
        if ds is None:
            print ("ERROR: can't open dataset" + DATASET)
        else:
            #trmm.get_stat(DATASET, SRC, DEST, TILE, EXTENT)
            data = trmm.get_data(ds,EXTENT)
            tif = trmm.create_tif(DEST+'/outall.tif', EXTENT, data, ds, etype=gdal.GDT_Float32)
            tif.GetRasterBand(1).SetNoDataValue(-9999.0)
    
