'''
Created on May 27, 2014

@author: theo
'''
import os,re,datetime
from .sat import Base

# MOD16 datasets
NTSG = 'ftp.ntsg.umt.edu'
WEEKLY = '/pub/MODIS/NTSG_Products/MOD16/MOD16A2.105_MERRAGMAO/'
YEARLY = '/pub/MODIS/NTSG_Products/MOD16/MOD16A3.105_MERRAGMAO/'
MONTHLY = '/pub/MODIS/NTSG_Products/MOD16/MOD16A2_MONTHLY.MERRA_GMAO_1kmALB/'
        
class MOD16(Base):

    def connect(self, host=NTSG, port=0, timeout=-999):
        Base.connect(self,host,port,timeout)
        
    def extractdate(self,name):
        ''' extract date from filename'''
        ypat = r'MOD16A3\.A(?P<year>\d{4})(?P<day>\d{3})\.'
        mpat = r'MOD16A2\.A(?P<year>\d{4})M(?P<month>\d{2})\.'
        dpat = r'MOD16A2\.A(?P<year>\d{4})(?P<day>\d{3})\.'
        m = re.search(ypat, name)
        if m is not None:
            year = int(m.group('year'))
            day = int(m.group('day'))
            return datetime.date(year-1,12,31)+datetime.timedelta(days=day)
        m = re.search(mpat, name)
        if m is not None:
            year = int(m.group('year'))
            month = int(m.group('month'))
            if month == 12:
                return datetime.date(year,12,31)
            return datetime.date(year,month+1,1)+datetime.timedelta(days=-1)
        m = re.search(dpat, name)
        if m is not None:
            year = int(m.group('year'))
            day = int(m.group('day'))
            return datetime.date(year-1,12,31)+datetime.timedelta(days=day)
        return None

    def download_yearly(self, folder, tile, first=2000, last=2015, overwrite = True):
        if not os.path.exists(folder):
            os.makedirs(folder)
        for year in range(first,last):
            self.ftp.cwd(YEARLY+'Y%d' % year)
            self.download_tile(folder, tile, overwrite)
            
    def download_monthly(self, folder, tile, first=2000, last=2015, overwrite = True):
        if not os.path.exists(folder):
            os.makedirs(folder)
        for year in range(first,last):
            for month in range(1,13):
                self.ftp.cwd(MONTHLY+'Y%d/M%02d' % (year,month))
                self.download_tile(folder, tile, overwrite)

    def download_weekly(self, folder, tile, first=2000, last=2015, overwrite = True):
        if not os.path.exists(folder):
            os.makedirs(folder)
        for year in range(first,last):
            for day in range(1,366,8):
                self.ftp.cwd(WEEKLY + 'Y%d/D%03d' % (year,day))
                self.download_tile(folder, tile, overwrite)
            
class MOD13(Base):
    
    def extractdate(self,name):
        pat = r'MOD13[ACQ][123]\.A(?P<year>\d{4})(?P<day>\d{3})\.[0-9\.]*hdf$'
        m = re.search(pat, name)
        if m is not None:
            year = int(m.group('year'))
            day = int(m.group('day'))
            return datetime.date(year-1,12,31)+datetime.timedelta(days=day)
        return None

class MOD15(Base):
    
    def extractdate(self,name):
        pat = r'MOD15A2H\.A(?P<year>\d{4})(?P<day>\d{3})\.'
        m = re.search(pat, name)
        if m is not None:
            year = int(m.group('year'))
            day = int(m.group('day'))
            return datetime.date(year-1,12,31)+datetime.timedelta(days=day)
        return None
