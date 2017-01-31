'''
Created on May 27, 2014

@author: theo
'''
import datetime
import calendar
import gzip
import os
import struct
import re
import numpy as np
import gdal, ogr, osr

# arc2 bounding box
BBOX = (-20, -40, 55, 40)
DELTA = (0.1, 0.1)
COLS = int((BBOX[2]-BBOX[0])/DELTA[0]) + 1
ROWS = int((BBOX[3]-BBOX[1])/DELTA[1]) + 1
SUFFIXES = ['min', 'max', 'mean', 'std', 'var', 'p']
PERCENTILES = [5,10,50,90,95]

class ARC2:

    def trans_lonlat(self,lon,lat):
        col = int((lon + DELTA[0]/2 - BBOX[0])/DELTA[0])
        row = int((lat + DELTA[1]/2 - BBOX[1])/DELTA[1])
        return (col, row)

    def trans_box(self,box):
        x1, y1 = self.trans_lonlat(box[0], box[1])
        x2, y2 = self.trans_lonlat(box[2], box[3])
        return (x1, y1, x2, y2)
    
    def trans_colrow(self,col,row):
        lon = BBOX[0] + col * DELTA[0]
        lat = BBOX[1] + row * DELTA[1]
        return (lon, lat)

    def trans_rect(self,box):
        x1, y1 = self.trans_colrow(box[0], box[1])
        x2, y2 = self.trans_colrow(box[2], box[3])
        return (x1, y1, x2, y2)
                    
    def torc(self, layer, bbox):
        ''' transform envelope to (row,col) and clip '''
        src = layer.GetSpatialRef()
        dest = osr.SpatialReference()
        dest.ImportFromEPSG(4326)
        trans = osr.CoordinateTransformation(src,dest)
        
        x1,y1,x2,y2 = bbox
        ll = trans.TransformPoint(x1,y1,0)
        ul = trans.TransformPoint(x1,y2,0)
        lr = trans.TransformPoint(x2,y1,0)
        ur = trans.TransformPoint(x2,y2,0)
        x1 = min(ll[0],ul[0])
        x2 = max(lr[0],ur[0])
        y1 = min(ll[1],lr[1])
        y2 = max(ul[1],ur[1])

        col1, row1 = self.trans_lonlat(x1,y1)
        col2, row2 = self.trans_lonlat(x2,y2)
        col1 = int(max(0,col1))
        col2 = int(min(COLS,col2))
        row1 = int(max(0,row1))
        row2 = int(min(ROWS,row2))

        if row1 > row2:
            return (col1,row2,col2,row1)
        else:
            return (col1,row1,col2,row2)

    def get_data(self,ds):
        fmt = '>%df' % (ROWS*COLS)
        with gzip.open(ds) as f:
            try:
                data = np.array(struct.unpack(fmt, f.read(4*ROWS*COLS))).reshape(ROWS,COLS)
                data[data<0] = float(0)
            except Exception as e:
                print e
                return None
        return data

    def get_timeseries(self, folder, lon, lat, start=datetime.date(1983,1,1), stop=datetime.date.today()):
        col, row = self.trans_lonlat(lon, lat)
        if col < 0 or col > COLS or row < 0 or row > ROWS:
            raise Exception('(lon,lat) out of range')
        
        PATTERN = r'daily_clim\.bin\.(?P<date>\d+)\.gz'
        series = []
        for path, dirs, files in os.walk(folder):
            files.sort()
            for file in files:
                match = re.search(PATTERN, file)
                if match:
                    date = match.group('date')
                    date = datetime.datetime.strptime(date,'%Y%m%d').date()
                    if date >= start and date <= stop:
                        data = self.get_data(os.path.join(path,file))
                        if data is None:
                            continue
                        series.append((date,data[row,col]))
        return series

    def dump_series(self, filename, src, extent, start=datetime.date(1983,1,1), stop=datetime.date.today(), aggregate=False, csv = True):
        col1, row1 = self.trans_lonlat(extent[0], extent[1])
        col2, row2 = self.trans_lonlat(extent[2], extent[3])
        col1 = max(0,col1)
        col2 = min(COLS,col2)
        row1 = max(0,row1)
        row2 = min(ROWS,row2)
        
        PATTERN = r'daily_clim\.bin\.(?P<date>\d+)\.gz'
        with open(filename,'w') as of:
            if csv:
                of.write('row,col,date,precipitation\n')
            else:
                of.write(','.join(['r%dc%d' % (r,c) for r in range(row1,row2) for c in range(col1,col2)]))
                of.write('\n')
            for path, dirs, files in os.walk(src):
                files.sort()
                for file in files:
                    match = re.search(PATTERN, file)
                    if match:
                        date = match.group('date')
                        date = datetime.datetime.strptime(date,'%Y%m%d').date()
                        if date >= start and date <= stop:
                            print file,
                            data = self.get_data(os.path.join(path,file))
                            if data is None:
                                continue
                            sum = 0
                            count = 0
                            
                            if not csv:
                                of.write(str(date))
                                
                            for r in range(row1,row2):
                                for c in range(col1,col2):
                                    if aggregate:
                                        sum += data[r,c]
                                        count += 1
                                    elif csv: 
                                        of.write('%d,%d,%s,%g\n' % (r,c,date,data[r,c]))
                                    else:
                                        of.write(',%g'%data[r,c])
                            if csv:
                                if aggregate and count>0:
                                    of.write('%s,%g\n'% (date,sum/count))
                            else:
                                of.write('\n')
                            print


    def dump_point_series(self, filename, src, loc, start=datetime.date(1983,1,1), stop=datetime.date.today()):
        col1, row1 = self.trans_lonlat(loc[0], loc[1])
        col1 = max(0,col1)
        row1 = max(0,row1)
        
        PATTERN = r'daily_clim\.bin\.(?P<date>\d+)\.gz'
        with open(filename,'w') as of:
            of.write('date,precipitation\n')
            for path, _, files in os.walk(src):
                files.sort()
                for fil in files:
                    match = re.search(PATTERN, fil)
                    if match:
                        date = match.group('date')
                        date = datetime.datetime.strptime(date,'%Y%m%d').date()
                        if date >= start and date <= stop:
                            print fil,
                            data = self.get_data(os.path.join(path,file))
                            if data is None:
                                continue
                            of.write('%s,%g\n' % (str(date), data[row1,col1]))
                            print


    def get_tiles(self, folder, extent, start=datetime.date(1983,1,1), stop=datetime.date.today()):
        PATTERN = r'daily_clim\.bin\.(?P<date>\d+)\.gz'
        x1,y1,x2,y2 = self.trans_box(extent)
        data = []
        for path, dirs, files in os.walk(folder):
            files.sort()
            for file in files:
                match = re.search(PATTERN, file)
                if match:
                    date = match.group('date')
                    date = datetime.datetime.strptime(date,'%Y%m%d').date()
                    if date > stop:
                        break
                    if date >= start:
                        print file
                        tile = self.get_data(os.path.join(path,file))
                        if tile is None:
                            continue
                        w = tile[y1:y2,x1:x2].copy() # no view: memory issues
                        data.append([date,w])
        return data
    
    def get_yearly_data(self, folder, extent, start=datetime.date(1983,1,1), stop=datetime.date.today()):
        tiles = self.get_tiles(folder, extent, start, stop)
        years = set([d.year for d,t in tiles])
        years = list(years)
        years.sort()
        result = {}
        for y in years:
            data = np.array([t for d,t in tiles if d.year == y])
            if data.shape[0] > 364:
                result[y] = data.sum(axis = 0)
        return result

    def get_yearly_mean(self, folder, extent, start=datetime.date(1983,1,1), stop=datetime.date.today()):
        ydict = self.get_yearly_data(folder, extent, start, stop)
        print 'got %s years' % len(ydict)
        data = np.array(ydict.values())
        data = data.mean(axis=0)
        return data
    
    def create_tif(self, filename, extent, data):
        dirname = os.path.dirname(filename)
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        ysize,xsize = data.shape
        tif = gdal.GetDriverByName('GTiff').Create(filename,xsize,ysize,eType=gdal.GDT_UInt16)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        tif.SetProjection(srs.ExportToWkt())
        tif.SetGeoTransform([extent[0],DELTA[0],0,extent[1],0,DELTA[1]])
        data = data.astype(np.uint16)
        tif.GetRasterBand(1).WriteArray(data)

    def basin_series(self, filename, src, basins, start=datetime.date(1983,1,1), stop=datetime.date.today()):

        PATTERN = r'daily_clim\.bin\.(?P<date>\d+)\.gz'
        features = sorted(basins.keys(),key = lambda f: f.GetFID())
        with open(filename,'w') as of:
            of.write('Date,')
            of.write(','.join([feature.GetField('NAME_2') for feature in features]))
            of.write('\n')
            for path, dirs, files in os.walk(src):
                files.sort()
                for file in files:
                    match = re.search(PATTERN, file)
                    if match:
                        date = match.group('date')
                        date = datetime.datetime.strptime(date,'%Y%m%d').date()
                        if date >= start and date <= stop:
                            print file,
                            data = self.get_data(os.path.join(path,file))
                            if data is None:
                                continue
                            of.write(str(date))
                            for feature in features:
                                sump = 0
                                sumw = 0
                                for c,r,w in basins[feature]:
                                    if w > 0:
                                        d = data[r,c]
                                        if d > 0:
                                            sump = sump + d * w
                                        sumw = sumw + w
                                value = sump / sumw if sumw > 0 else -9999
                                of.write(',%g' % value)
                            of.write('\n')
                            print

    def get_weights(self, geom):
        weights = []
        x1,x2,y1,y2 = geom.GetEnvelope() # must be in lonlat
        if x1 > x2:
            t = x1
            x1 = x2
            x2 = t
        if y1 > y2:
            t = y1
            y1 = y2
            y2 = t
        x1 = int(x1 * 10.0) / 10.0
        y1 = int(y1 * 10.0) / 10.0
        for y in np.arange(y1-0.05, y2, 0.1):
            for x in np.arange(x1-0.05, x2, 0.1):
                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(x,y)
                ring.AddPoint(x,y+0.1)
                ring.AddPoint(x+0.1,y+0.1)
                ring.AddPoint(x+0.1,y)
                ring.AddPoint(x,y)
                poly = ogr.Geometry(ogr.wkbPolygon)
                poly.AddGeometry(ring)
                if geom.Contains(poly):
                    frac = 1.0
                else:
                    isect = poly.Intersection(geom)
                    if isect.IsEmpty():
                        frac = 0.0
                    else:
                        frac = isect.GetArea() / poly.GetArea()
                if frac != 0:
                    c,r = self.trans_lonlat(x,y)
                    weights.append([c,r,frac])
        return weights

    def do_save_stats(self, filename, data, extent,agg):
        dirname = os.path.dirname(filename)
        if os.path.exists(filename):
            os.remove(filename)
        elif not os.path.exists(dirname):
            os.makedirs(dirname)
        adata = agg(axis=0)
        ysize,xsize = adata.shape
        tif = gdal.GetDriverByName('GTiff').Create(filename,xsize,ysize,eType=gdal.GDT_Float32)
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        tif.SetProjection(srs.ExportToWkt())
        tif.SetGeoTransform([extent[0],DELTA[0],0,extent[1],0,DELTA[1]])
        tif.GetRasterBand(1).WriteArray(adata.astype(np.float32))
        
    def save_stats(self, dest, data, extent):
        for suffix in SUFFIXES:
            if suffix == 'p':
                for q in PERCENTILES:
                    def agg(axis=0):
                        return np.percentile(data, q, axis)
                    filename = '%s.%s%d.tif' % (dest, suffix, q)
                    print filename
                    self.do_save_stats(filename, data, extent, agg)
            else:
                agg = getattr(data,suffix)
                filename = '%s.%s.tif' % (dest, suffix)
                print filename
                self.do_save_stats(filename, data, extent, agg)
        
    def get_stat(self, folder, dest, extent=None, start=None, stop=None):
        
        tiles = self.get_tiles(folder,extent,start,stop)
        years = set([d.year for d,t in tiles])

        sums = []
        for y in years:
            data = np.array([t for d,t in tiles if d.year == y])
            # daily statistics per year
            self.save_stats('%s.%d' % (dest, y), data, extent)

            if data.shape[0] > 364:
                sums.append(data.sum(axis=0))

        # year statistics
        self.save_stats('%s.yearly' % (dest), np.array(sums), extent)

        # month statistics
        for m in range(1,13):
            sums = []
            month = calendar.month_abbr[m]
            for y in years:
                data = np.array([t for d,t in tiles if d.year == y and d.month == m])
                if data.shape[0] > 27:
                    sums.append(data.sum(axis=0))
            self.save_stats('%s.%s' % (dest, month), np.array(sums), extent)

        # daily statistics for entire period
        data = [t for d,t in tiles]
        self.save_stats('%s.daily'% (dest), np.array(data), extent)

