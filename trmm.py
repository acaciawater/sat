'''
Created on Jan 6, 2016

@author: theo
'''
import re, datetime, osr
from sat import Base

class TRMM(Base):

    def __init__(self, filename = None):
        Base.__init__(self,filename)
        # set default spatial reference
        sr = osr.SpatialReference()
        sr.ImportFromEPSG(4326)
        self.wgs84 = sr.ExportToWkt()
        
    def get_dataset(self, name):
        ds = Base.get_dataset(self, name)
        if ds:
            if not ds.GetProjection():
                ds.SetProjection(self.wgs84)
        return ds
    
    
    def extractdate(self,name):
        ''' extract date from filename'''
        pat = r'3B43\.(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})\.'
        m = re.search(pat, name)
        if m is not None:
            year = int(m.group('year'))
            month = int(m.group('month'))
            day = int(m.group('day'))
            return datetime.date(year,month,day)
        return None

 
if __name__ == '__main__':
    trmm = TRMM()
    AFRICA = (-20,-36,55,38)
    trmm.get_stat('pcp', '/media/sf_F_DRIVE/projdirs/NAGA/TRMM','/media/sf_F_DRIVE/projdirs/NAGA/TRMM/stat', None, AFRICA, start=datetime.date(2000,1,1),stop=datetime.date(2015,12,31))
