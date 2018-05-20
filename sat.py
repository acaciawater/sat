'''
Created on Jan 6, 2016

@author: theo
'''
import gdal, osr, ogr
import os,datetime,calendar
import numpy as np
from ftplib import FTP

class Base:

    def __init__(self, filename=None):
        self.ftp = None
        if filename is not None:
            self.open(filename)

    def open(self, filename):
        self.hdf = gdal.OpenShared(filename)
        return self.hdf is not None

    def close(self):
        self.hdf = None
            
    def get_dataset(self, name):
        sets = self.hdf.GetMetadata('SUBDATASETS')
        i = 1
        while True:
            key = 'SUBDATASET_%d_DESC' % i
            if not key in sets:
                break
            desc = sets[key]
            if name in desc:
                key = 'SUBDATASET_%d_NAME' % i
                name = sets[key]
                return gdal.OpenShared(name)
            i += 1
        return None

    def transbox(self, ds, bbox, topix=False, clip=False):
        ''' transform bounding box coordinates in lonlat to projected coordinates or pixel coordinates '''
        src = osr.SpatialReference()
        src.ImportFromEPSG(4326)
        dest = osr.SpatialReference()
        dsproj = ds.GetProjection()
        dest.ImportFromWkt(dsproj)
        trans = osr.CoordinateTransformation(src,dest)
        
        x1,y1,x2,y2 = bbox
        ll = trans.TransformPoint(x1,y1)
        ul = trans.TransformPoint(x1,y2)
        lr = trans.TransformPoint(x2,y1)
        ur = trans.TransformPoint(x2,y2)
        
        x1 = min(ll[0],ul[0])
        x2 = max(lr[0],ur[0])
        y1 = min(ll[1],lr[1])
        y2 = max(ul[1],ur[1])

        if clip or topix:
            fwd = ds.GetGeoTransform()
            inv = gdal.InvGeoTransform(fwd)
            px1,py1 = gdal.ApplyGeoTransform(inv,x1,y1)
            px2,py2 = gdal.ApplyGeoTransform(inv,x2,y2)
            if py1 > py2:
                t = py1
                py1 = py2
                py2 = t
            if clip:
                px1 = int(max(0,px1))
                py1 = int(max(0,py1))
                px2 = int(min(ds.RasterXSize-1,px2))
                py2 = int(min(ds.RasterYSize-1,py2))
                
            if topix:
                x1 = px1
                y1 = py1
                x2 = px2
                y2 = py2
            else:
                x1,y1 = gdal.ApplyGeoTransform(fwd,px1,py1)
                x2,y2 = gdal.ApplyGeoTransform(fwd,px2,py2)

        if y1 > y2:
            return (x1,y2,x2,y1)
        else:
            return (x1,y1,x2,y2)

    def get_data(self,ds,bbox=None):

        if isinstance(ds,str):
            ds = self.get_dataset(ds)

        band = ds.GetRasterBand(1)
        if bbox is None:
            return band.ReadAsArray()

        x1,y1,x2,y2 = self.transbox(ds, bbox, topix=True, clip=True)

        xoff = int(x1)
        xsize = int(x2-x1)+1
        yoff = int(y1)
        ysize = int(y2-y1)+1

        return band.ReadAsArray(xoff,yoff,xsize,ysize)

    def connect(self, host, port=0, timeout=-999):
        if self.ftp is None:
            self.ftp = FTP()
        self.ftp.connect(host, port, timeout)
        self.ftp.login()
        return self.ftp

    def disconnect(self):
        if self.ftp is not None:
            self.ftp.close()
            self.ftp = None

    def download(self, filename, folder, overwrite=True):
        print (filename)
        pathname = os.path.join(folder,filename)
        if os.path.exists(pathname):
            if not overwrite:
                print (pathname + ' exists')
                return
        with open(pathname,'wb') as f:
            def save(data):
                f.write(data)
            self.ftp.retrbinary('RETR '+ filename, save)

    def download_tile(self, folder, tile, overwrite = True):
        files = self.ftp.nlst()
        for filename in files:
            if tile is None or tile in filename:
                self.download(filename, folder, overwrite)
                break

    def getcolrow(self,ds,lon,lat):
        proj = ds.GetProjection()
        src = osr.SpatialReference()
        src.ImportFromEPSG(4326)
        dest = osr.SpatialReference()
        dest.ImportFromWkt(proj)
        trans = osr.CoordinateTransformation(src,dest)
        
        x,y,z = trans.TransformPoint(lon,lat)

        inv = gdal.InvGeoTransform(ds.GetGeoTransform())

        return gdal.ApplyGeoTransform(inv,x,y)
    
    def extractdate(self,name):
        return None

    def is_datafile(self,filename):
        return self.extractdate(filename)
        
    def save_timeseries(self, dataset, folder, tile, lonlat, dest, start=datetime.date(2000,1,1), stop=datetime.date.today()):
        count = 0
        dest.write(','.join(['Date', dataset])+ '\n')
        lon,lat = lonlat
        for path, dirs, files in os.walk(folder):
            files.sort()
            for fil in files:
                if self.is_datafile(fil) and (tile is None or tile in fil):
                    date = self.extractdate(fil)
                    if start is not None:
                        if start > date:
                            continue
                    if stop is not None:
                        if stop < date:
                            continue
                    print (fil)
                    if not self.open(os.path.join(path,fil)):
                        print ("ERROR: can't open file " + fil)
                        continue
                    ds = self.get_dataset(dataset)
                    if ds is None:
                        print ('ERROR: cant open dataset ' + dataset)
                        continue                
                    if count == 0:
                        x,y = self.getcolrow(ds, lon, lat)
                    if x < 0 or y < 0 or x >= ds.RasterXSize or y >= ds.RasterYSize:
                        print ('ERROR: lon,lat not in tile')
                        break
                    
                    count = count+1
                    band = ds.GetRasterBand(1)
                    data = band.ReadAsArray(int(x),int(y),1,1)
                    dest.write('%s,%g\n' % (date or fil, data[0][0]))
    
    def get_geotransform(self, dataset, extent=None):
        ''' get the geotransform of a dataset for a given extent '''
        trans = list(dataset.GetGeoTransform())
        if extent is not None:
            box = self.transbox(dataset, extent, topix=False, clip=True)
            trans[0] = box[0]
            trans[3] = box[3]
        return trans
    
    def copy_projection(self, source, dest, extent=None):
        ''' copy projection and geotransform for given extent from source to dest dataset '''
        dest.SetProjection(source.GetProjection())
        trans = self.get_geotransform(source, extent)
        dest.SetGeoTransform(trans)

    def get_tiff(self, dataset, folder, extent, agg='mean', eType=gdal.GDT_Int16):
        ''' cut extent out of a dataset and aggregate values '''
        count = 0
        tif = None
        data = []
        for path, dirs, files in os.walk(folder):
            files.sort()
            for fil in files:
                if not self.is_datafile(fil):
                    continue
                print (fil)
                self.open(os.path.join(path,fil))
                ds = self.get_dataset(dataset)
                tile = self.get_data(ds, extent) # 2-dimensional np.ndarray
                count += 1
                if tif is None:
                    ysize,xsize = tile.shape
                    tif = gdal.GetDriverByName('GTiff').Create(os.path.join(folder, dataset+'.tif'), xsize, ysize, eType=eType)
                    self.copy_projection(ds,tif,extent)
                data.append(tile)
        if tif is not None:
            band = tif.GetRasterBand(1)
            data = np.array(data)
            ag = data.mean(axis=0)
            band.WriteArray(ag)

    def extract(self, dataset, folder, extent, eType=gdal.GDT_Int16, overwrite=False):
        ''' extract dataset and save as geotiff '''
        for path, dirs, files in os.walk(folder):
            files.sort()
            for fil in files:
                if not self.is_datafile(fil):
                    continue
                dest = os.path.join(folder, '%s.%s.tif' % (os.path.splitext(fil)[0], dataset))
                if os.path.exists(dest):
                    if overwrite:
                        os.remove(dest)
                    else:
                        continue
                print (fil)
                try:
                    self.open(os.path.join(path,fil))
                    ds = self.get_dataset(dataset)
                    tile = self.get_data(ds, extent) # 2-dimensional np.ndarray
                    ysize,xsize = tile.shape
                    tif = gdal.GetDriverByName('GTiff').Create(dest, xsize, ysize, eType=eType)
                    self.copy_projection(ds, tif, extent)
                    band = tif.GetRasterBand(1)
                    band.WriteArray(np.array(tile))
                except Exception as e:
                    print ('ERROR: ' + str(e))

    def create_tif(self, filename, extent, data, template, etype):

        if os.path.exists(filename):
            os.remove(filename)
        else:
            dirname = os.path.dirname(filename)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        print (filename)
        ysize,xsize = data.shape
        tif = gdal.GetDriverByName('GTiff').Create(filename, xsize, ysize, eType=etype)
        self.copy_projection(template, tif, extent)
        band = tif.GetRasterBand(1)
        band.WriteArray(data)
             
    def save_stats(self, dest, data, extent, template):
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
        self.create_tif(dest+'.min.tif',extent,mn,template,gdal.GDT_Float32)
        self.create_tif(dest+'.max.tif',extent,mx,template,gdal.GDT_Float32)
        self.create_tif(dest+'.mean.tif',extent,mean,template,gdal.GDT_Float32)
        self.create_tif(dest+'.std.tif',extent,std,template,gdal.GDT_Float32)
        self.create_tif(dest+'.var.tif',extent,var,template,gdal.GDT_Float32)

        try:
            # not tested!
            md = np.median(data)
            self.create_tif(dest+'.med.tif',extent,md,template,gdal.GDT_Float32)
        except:
            pass
        
    def get_stat(self, dataset, folder, dest, tile, extent=None, start=None, stop=None, grouper=None):
        tiles = []
        template = None

        for path, _, files in os.walk(folder):
            files.sort()
            for fil in files:
                if self.is_datafile(fil) and (tile is None or tile in fil):
                    date = self.extractdate(fil)
                    if start is not None:
                        if start > date:
                            continue
                    if stop is not None:
                        if stop < date:
                            continue
    
                    print (fil)
                    if not self.open(os.path.join(path,fil)):
                        print (" ERROR: can't open file")
                        continue
                    ds = self.get_dataset(dataset)
                    if ds is None:
                        print ('ERROR: cant open dataset.')
                        continue
                    if template is None:
                        template = ds
                    data = self.get_data(ds, extent) # 2-dimensional np.ndarray
                    tiles.append((date,data))

        name = '{path}/{name}'.format(path=dest, name=dataset)
        if tile:
            name = '{name}.{tile}'.format(name=name, tile=tile)

        # overall stats
        data = [t for d,t in tiles]
        self.save_stats(name, data, extent, template)
       
        # month statistics
        months = set([d.month for d,t in tiles])
        for m in months:
            month = calendar.month_abbr[m]
            data = [t for d,t in tiles if d.month == m]
            filename = '{name}.{month}'.format(name=name,month=month)
            self.save_stats(filename, data, extent, template)

        # statistics per year
        if grouper is None:
            grouper = lambda d: d.year
        years = set([grouper(d) for d,t in tiles])
        for y in years:
            data = [t for d,t in tiles if grouper(d) == y]
            filename = '{name}.{year}'.format(name=name, year=y)
            self.save_stats(filename, data, extent, template)

    def tileid(self, lon, lat):
        ''' determine tile id from lon lat
            (0-10,0-10) = h18v08
        '''
        h = int((lon + 180) / 10)
        v = int((90 - lat) / 10)
        return 'h{:02d}v{:02d}'.format(h,v)
        
    def point_series(self, shapefile, csvfile, modis_folder, dataset='NDVI', start=datetime.date(2000,1,1), stop=datetime.date.today()):
        ''' generate timeseries for points in shapefile '''
        
        # collect coordinates and determine tile ids
        shp = ogr.Open(shapefile)
        layer= shp.GetLayer(0)
        pts = {}
        for feature in layer:
            fid = feature.GetFID()
            geom = feature.GetGeometryRef()
            x,y,z = geom.Centroid().GetPoint()
            pts[fid] = {'lon': x, 'lat': y, 'tile': self.tileid(x,y)}
            print (fid,pts[fid])
            
        with open(csvfile,'w') as of:
            # write csv header line
            of.write('FID,lon,lat,tile,col,row,date,{}\n'.format(dataset))
            # loop over all modis files in source folder
            for path, _, files in os.walk(modis_folder):
                files.sort()
                for fil in files:
                    date = self.extractdate(fil)
                    if date is None or date < start or date > stop:
                        continue
                    data = None
                    for fid, p in pts.iteritems():
                        if p['tile'] in fil:
                            # matching tile and date
                            print (fil)
                            if data is None:
                                try:
                                    self.open(os.path.join(path,fil))
                                    ds = self.get_dataset(dataset)
                                    data = self.get_data(ds)
                                except Exception as e:
                                    print *'ERROR opening file ' + str(e)
                                    continue
                            if not 'row' in p:
                                lon = p['lon']
                                lat = p['lat']
                                col,row = self.getcolrow(ds, lon, lat)
                                col = int(col)
                                row = int(row)
                                p['col'] = col
                                p['row'] = row
                                #print fid, lon, lat, col, row
                            row = p['row']
                            col = p['col']
                            value = data[row,col]
                            of.write('{},{},{},{},{},{},{},{}\n'.format(fid,p['lon'],p['lat'],p['tile'],p['col'],p['row'],date,value))
                            print   
    
                               
    def polygon_series(self, filename, weights, src, dataset='NDVI', tile='h22v08', start=datetime.date(2000,1,1), stop=datetime.date.today()):
        '''
        Generate mean timeseries for dataset in given polygon features
        filename = destination filename
        src = source folder for hdf files
        weights = dict with pixel weights per polygon feature
        tile = tile id
        '''
        
        features = sorted(weights.keys(),key = lambda f: f.GetFID())
        with open(filename,'w') as of:
            of.write('Date,')
            of.write(','.join(['%d' % feature.GetFID() for feature in features]))
            of.write('\n')
            for path, _, files in os.walk(src):
                files.sort()
                for file in files:
                    if self.is_datafile(file) and (tile is None or tile in file):
                        date = self.extractdate(file)
                        if date >= start and date <= stop:
                            print (file)
                            try:
                                self.open(os.path.join(src,file))
                                data = self.get_data(dataset)
                            except:
                                # skip errors in file
                                continue
                            of.write(str(date))
                            for feature in features:
                                sump = 0
                                sumw = 0
                                for c,r,w in weights[feature]:
                                    if w > 0:
                                        d = data[r,c]
                                        if d > 0 and d < 32000:
                                            sump = sump + d * w
                                        sumw = sumw + w
                                value = sump / sumw if sumw > 0 else -9999
                                of.write(',%g' % value)
                            of.write('\n')
            
    def get_weights(self, ds, geom):
        fwd = ds.GetGeoTransform()
        _,inv = gdal.InvGeoTransform(fwd)
        x1,x2,y1,y2 = geom.GetEnvelope()
        px1, py1 = gdal.ApplyGeoTransform(inv,x1,y1)
        px2, py2 = gdal.ApplyGeoTransform(inv,x2,y2)
        if py2 < py1:
            t = py1
            py1 = py2
            py2 = t

        px1 = max(0,px1)
        py1 = max(0,py1)
        px2 = min(ds.RasterXSize,px2)
        py2 = min(ds.RasterYSize,py2)

        if px2<px1 or py2<py1:
            return []

        weights = []
        for y in range(int(py1),int(py2)):
            for x in range(int(px1),int(px2)):
                x1,y1 = gdal.ApplyGeoTransform(fwd,x,y)
                x2,y2 = gdal.ApplyGeoTransform(fwd,x+1,y+1)
                ring = ogr.Geometry(ogr.wkbLinearRing)
                ring.AddPoint(x1,y1)
                ring.AddPoint(x1,y2)
                ring.AddPoint(x2,y2)
                ring.AddPoint(x2,y1)
                ring.AddPoint(x1,y1)
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
                    weights.append([x,y,frac])
        return weights

    def shape_series(self, csvfile, modis_folder, shapefile, dataset_name, tile, start=datetime.date(2000,1,1), stop=datetime.date.today()):
        '''
        Generate mean timeseries for modis dataset and polygon features in shapefile
        csvfile = destination file
        modis_folder = source folder for modis hdf files
        shapefile = shapefile with polygon features (must have same CRS as modis files)
        dataset_name = modis dataset (e.g. 'NDVI' or 'PET_1km'
        tile = modis tile id (e.g. 'h22v08')
        '''
        shp = ogr.Open(shapefile)
        layer= shp.GetLayer(0)
        weights = {}
        ds = None
        
        # get sample tile for coordinates
        for path,dirs,files in os.walk(modis_folder):
            for filename in files:
                if self.is_datafile(filename) and (tile is None or tile in filename):
                    if self.open(os.path.join(path,filename)):
                        ds = self.get_dataset(dataset_name)
                        break
            break
        if ds is None:
            print ('No tiles found')
            exit
        
        print ('calculating weights...')
        found = 0
        for feature in layer:
            print ('feature ' + str(feature.GetFID()))
            geom = feature.GetGeometryRef()
            w = self.get_weights(ds,geom)
            found += len(w)
            weights[feature] = w

        if found == 0:
            print ('No intersecting features found for tile %s' % tile)
        else:
            self.polygon_series(csvfile, weights, modis_folder, dataset_name, tile, start, stop)
