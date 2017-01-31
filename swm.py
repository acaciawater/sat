'''
Created on Jan 7, 2016

@author: theo
'''
from trmm import TRMM
from modis import MOD16

PARAMARIBO=(-55.2,5.9)
SURINAME = (-58.5,1.5,-54,6.5)

def trmm_paramaribo():
    trmm = TRMM()
    with open('paramaribo.csv','w') as dest:
        trmm.save_timeseries('pcp', '/home/theo/trmm', None, PARAMARIBO, dest)

def trmm_stat():    
    trmm = TRMM()
    trmm.get_stat('pcp', '/home/theo/trmm','/home/theo/trmm', None, SURINAME)

def down_modis(): 
    mod = MOD16()
    mod.connect()
    mod.download_yearly('/media/sf_F_DRIVE/projdirs/SWM/MODIS', 'h12v08', overwrite=False)

def mod_stat():
    mod = MOD16()
    mod.get_stat('ET_1km', '/media/sf_F_DRIVE/projdirs/SWM/MODIS', '/media/sf_F_DRIVE/projdirs/SWM/MODIS', 'h12v08', SURINAME)
    mod.get_stat('PET_1km', '/media/sf_F_DRIVE/projdirs/SWM/MODIS', '/media/sf_F_DRIVE/projdirs/SWM/MODIS', 'h12v08', SURINAME)
    
if __name__ == '__main__':
    down_modis()
    mod_stat()
    