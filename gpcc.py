'''
Created on Jun 10, 2016

@author: theo
'''
import os, re, datetime,calendar
import numpy as np
import gdal, osr

DELTA = (0.5, -0.5)
EXTENT = (-180,90,180,-90)
DIMX = 360*2
DIMY = 180*2

def create_tif(filename, data):
    dirname = os.path.dirname(filename)
    if not os.path.exists(dirname):
        os.makedirs(dirname)
    if os.path.exists(filename):
        os.remove(filename)
    ysize,xsize = data.shape
    tif = gdal.GetDriverByName('GTiff').Create(filename,xsize,ysize,eType=gdal.GDT_Float32)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    tif.SetProjection(srs.ExportToWkt())
    tif.SetGeoTransform([EXTENT[0],DELTA[0],0,EXTENT[1],0,DELTA[1]])
    data = data.astype(np.float32)
    tif.GetRasterBand(1).WriteArray(data)

def getdata(src):
    with open(src,'r') as f:
        for i in range(14):
            f.readline()
        data = np.ndarray((DIMY,DIMX),dtype=np.float32)
        for y in range(DIMY):
            for x in range(DIMX):
                words = f.readline().split()
                prec = float(words[0])
                if prec < 0:
                    prec = np.nan
                data[y][x] = prec
    return data

def extractdate(name):
    ''' extract date from filename'''
    '''gpcc_full_data_v006_05_degree_012001'''
    
    pat = r'_(?P<month>\d{2})(?P<year>\d{4})$'
    m = re.search(pat, name)
    if m is not None:
        year = int(m.group('year'))
        month = int(m.group('month'))
        return datetime.date(year,month,1)
    return None
    
def gpcc2tif(src,dest):
    for path, dirs, files in os.walk(src):
        for fil in files:
            srcfil = os.path.join(src,fil)
            destfil = os.path.join(dest, '%s.tif' % (os.path.splitext(fil)[0]))
            print fil
            if extractdate(fil):
                create_tif(destfil,EXTENT,getdata(srcfil))

def save_stats(dest, data):
    sm = sm2 = mn = mx = None
    count = len(data)
    if count == 0:
        return
    for raster in data:
        # force 32 bits floating point
        tile = raster.astype(np.float32)
        if sm is None:
            sm = np.copy(tile)
            sm2 = np.square(tile)
            mn = np.copy(tile)
            mx = np.copy(tile)
        else:
            sm = np.add(sm,tile)
            sm2 = np.add(sm2,np.square(tile))
            mn = np.minimum(mn, tile)
            mx = np.maximum(mx, tile)
    mean = sm / count
    var = np.subtract(sm2 / count, np.square(mean))
    try:
        std = np.sqrt(var)
    except:
        std = np.zeros(len(var))
    #variation = np.divide(std, mean)

    create_tif(dest+'.min.tif',mn)
    create_tif(dest+'.max.tif',mx)
    create_tif(dest+'.mean.tif',mean)
    create_tif(dest+'.std.tif',std)
    create_tif(dest+'.var.tif',var)

def gpccstat(src,dest,grouper=None):
    tiles = []
    for path, dirs, files in os.walk(src):
        for fil in files:
            date = extractdate(fil)
            if not date:
                continue
            print fil
            srcfil = os.path.join(src,fil)
            data = getdata(srcfil)
            tiles.append((date,data))

    # month statistics
    months = set([d.month for d,t in tiles])
    for m in months:
        month = calendar.month_abbr[m]
        data = [t for d,t in tiles if d.month == m]
        filename = os.path.join(dest,'{name}.{month}'.format(name='gpcc',month=month))
        save_stats(filename, data)

    # statistics per year
    if grouper is None:
        grouper = lambda d: d.year
    years = set([grouper(d) for d,t in tiles])
    yearsum = []
    for y in years:
        data = np.array([t for d,t in tiles if grouper(d) == y])
        yearsum.append(data.sum(axis=0))
        filename = os.path.join(dest,'{name}.{year}'.format(name='gpcc', year=y))
        save_stats(filename, data)

    # overall stats        
    filename = os.path.join(dest,'gpcc')
    save_stats(filename, yearsum)
   
SRC = '/media/sf_F_DRIVE/projdirs/NAGA/gpcc_full_data_archive_v006_05_degree_2001_2010'
DEST = '/media/sf_F_DRIVE/projdirs/NAGA/gpcc_full_data_archive_v006_05_degree_2001_2010/stat'

if __name__ == '__main__':
    gpccstat(SRC,DEST)