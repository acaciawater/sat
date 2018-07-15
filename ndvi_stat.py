from .modis import MOD13

EXTENT=(33,3,48,15) # Ethiopia

SRC = r'D:\rawdata\africa\ethiopia\MODIS\MOD13.A3.006'
DEST = r'D:\rawdata\africa\ethiopia\MODIS\MOD13.A3.006\stat'
TILES = ('h21v07','h22v07','h21v08','h22v08')

mod = MOD13()
for tile in TILES:
    mod.get_stat('NDVI', SRC, DEST, tile, EXTENT)
