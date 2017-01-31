'''
Created on Apr 28, 2016

@author: theo
'''
import os,re, sys
import gdal
import numpy as np
from scipy.stats import linregress

SRC = r'G:/GIS_bestanden/Africa/modis/ndvi/mod13a3.005'
PATTERN = r'NDVI\.(?P<tile>h\d{2}v\d{2})\.(?P<year>\d{4})\.mean\.tif$'

def save(folder,name,data,template,eType=gdal.GDT_Float32):
    ysize,xsize = data.shape
    filename = os.path.join(folder, name+'.tif')
    if os.path.exists(filename):
        os.remove(filename)
    tif = gdal.GetDriverByName('GTiff').Create(filename, xsize, ysize, eType=eType)
    tif.SetProjection(template.GetProjection())
    tif.SetGeoTransform(template.GetGeoTransform())
    band = tif.GetRasterBand(1)
    band.WriteArray(data)
    tif = None

def process_tile(tile, items):
    data = {}
    template = None
    print 'Processing',tile
    for year, filename in items.items():
        ds = gdal.OpenShared(filename)
        if template is None:
            template = ds
        band = ds.GetRasterBand(1)
        data[year] = band.ReadAsArray()
        
    # calculate trend
    years = data.keys()
    dim = data[years[0]].shape
    height,width = dim
    slope = np.ndarray(dim,dtype=np.float32)
    correl = np.ndarray(dim,dtype=np.float32)
    stderr = np.ndarray(dim,dtype=np.float32)
    pval = np.ndarray(dim,dtype=np.float32)
    for i in range(height):
        #sys.stderr.write('\r%d   ' % (height-i))
        for j in range(width):
            values = [data[y][i][j] for y in years]
            rc, intercept, rvalue, pvalue, evalue = linregress(years, values)
            slope[i][j] = rc
            correl[i][j] = rvalue
            stderr[i][j] = evalue
            pval[i][j] = pvalue
    save(SRC,'slope/NDVI.{tile}.slope'.format(tile=tile), slope, template)
    save(SRC,'correl/NDVI.{tile}.correl'.format(tile=tile), correl, template)
    save(SRC,'stderr/NDVI.{tile}.stderr'.format(tile=tile), stderr, template)
    save(SRC,'pvalue/NDVI.{tile}.pvalue'.format(tile=tile), pval, template)

    return tile

TILES = ('h23v08',)

if __name__ == '__main__':
    tiles = {}
    for path, dirs, files in os.walk(SRC):
        for fil in files:
            m = re.search(PATTERN, fil)
            if m is not None:
                year = int(m.group('year'))
                if year > 2015:
                    continue
                tile = m.group('tile')
##                if not tile in TILES:
##                    continue
                dataset = os.path.join(path,fil)
                if not tile in tiles:
                    tiles[tile] = {year:dataset}
                else:
                    tiles[tile][year] = dataset

    import multiprocessing as mp
    pool = mp.Pool(4)
    results = []
    for tile, data in tiles.items():
        results.append(pool.apply_async(process_tile, (tile, data)))
    for result in results:
        tile = result.get()
        print 'tile %s completed' % tile
