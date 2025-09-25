
import urllib
import requests
from datetime import datetime
from scipy.signal import savgol_filter
from scipy import interpolate as scipy_interpolate
from tqdm import tqdm
import xarray as xr
import pandas as pd
import numpy as np
import os, glob
import zipfile
import pandas as pd
import rasterio
import json
import rioxarray
import calendar
import pyproj
from json import load
from pyproj import Transformer
from pystac_client import Client
from shapely.ops import transform
import shapely
from shapely.geometry import box
from shapely.geometry import shape

import warnings
warnings.filterwarnings("ignore", 
                       message="invalid value encountered in cast",
                       category=RuntimeWarning,
                       module="xarray.core.duck_array_ops")

warnings.filterwarnings('ignore', category=RuntimeWarning)

cloud_dict = {
    'S2-16D-2':{
        'cloud_band': 'SCL',
        'non_cloud_values': [4,5,6],
        'cloud_values': [0,1,2,3,7,8,9,10,11]
    },
    'S2_L2A-1':{
        'cloud_band': 'SCL',
        'non_cloud_values': [4,5,6],
        'cloud_values': [0,1,2,3,7,8,9,10,11]
    },
    'LANDSAT-16D-1':{
        'cloud_band': 'qa_pixel',
        'non_cloud_values': [6,7],
        'cloud_values': [0,1,2,3,4,5]
    },
    'landsat-2':{
        'cloud_band': 'qa_pixel',
        'non_cloud_values': [6,7],
        'cloud_values': [0,1,2,3,4,5]
    },
    'AMZ1-WFI-L4-SR-1':{
        'cloud_band': 'CMASK',
        'non_cloud_values': [127],
        'cloud_values': [255, 0],
        'no_data_value': 0
    }
}

bands_dict = {
  "S2": {
    "B01": { "name": "coastal" },
    "B02": { "name": "blue" },
    "B03": { "name": "green" },
    "B04": { "name": "red" },
    "B05": { "name": "red-edge-1" },
    "B06": { "name": "red-edge-2" },
    "B07": { "name": "red-edge-3" },
    "B08": { "name": "nir" },
    "B8A": { "name": "narrow-nir" },
    "B09": { "name": "water-vapour" },
    "B10": { "name": "swir-cirrus" },
    "B11": { "name": "swir-1" },
    "B12": { "name": "swir-2" },
    "NDVI": { "name": "ndvi" },
    "EVI": { "name": "evi" },
    "NBR": { "name": "nbr" },
  },
 "SAMET":{
     "tmax": { "name": "tmax" },
     "tmin": { "name": "tmin" },
     "tmean": { "name": "tmean" },
     "thumbnail": { "name": "thumbnail" }
 }
}

coverage_proj = pyproj.CRS.from_wkt('''
    PROJCS["unknown",
        GEOGCS["unknown",
            DATUM["Unknown based on GRS80 ellipsoid",
                SPHEROID["GRS 1980",6378137,298.257222101,
                    AUTHORITY["EPSG","7019"]]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.0174532925199433,
                AUTHORITY["EPSG","9122"]]],
        PROJECTION["Albers_Conic_Equal_Area"],
        PARAMETER["latitude_of_center",-12],
        PARAMETER["longitude_of_center",-54],
        PARAMETER["standard_parallel_1",-2],
        PARAMETER["standard_parallel_2",-22],
        PARAMETER["false_easting",5000000],
        PARAMETER["false_northing",10000000],
        UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
        AXIS["Easting",EAST],
        AXIS["Northing",NORTH]]''')

stac = Client.open("https://data.inpe.br/bdc/stac/v1")

def collection_query(collection, start_date, end_date, tile=None, bbox=None, freq=None, bands=None):
    """An object that contains the information associated with a collection 
    that can be downloaded or acessed.

    Args:
        collection : String containing a collection id.

        start_date String containing the start date of the associated collection. Following YYYY-MM-DD structure.

        end_date : String containing the start date of the associated collection. Following YYYY-MM-DD structure.

        freq : Optional, string containing the frequency of images of the associated collection. Following (days)D structure. 

        bands : Optional, string containing the list bands id.
    """

    return dict(
        collection = collection,
        bands = bands,
        start_date = start_date,
        tile = tile,
        bbox = bbox,
        end_date = end_date
    )

def download_stream(file_path: str, response, chunk_size=1024*64, progress=True, offset=0, total_size=None):
    """Download request stream data to disk.

    Args:
        file_path - Absolute file path to save
        response - HTTP Response object
    """
    parent = os.path.dirname(file_path)

    if parent:
        os.makedirs(parent, exist_ok=True)

    if not total_size:
        total_size = int(response.headers.get('Content-Length', 0))

    file_name = os.path.basename(file_path)

    progress_bar = tqdm(
        desc=file_name[:30]+'... ',
        total=total_size,
        unit="B",
        unit_scale=True,
        #disable=not progress,
        initial=offset,
        disable=True
    )

    mode = 'a+b' if offset else 'wb'

    # May throw exception for read-only directory
    with response:
        with open(file_path, mode) as stream:
            for chunk in response.iter_content(chunk_size):
                stream.write(chunk)
                progress_bar.update(chunk_size)

    #file_size = os.stat(file_path).st_size

    #if file_size != total_size:
    #    os.remove(file_path)
    #    raise IOError(f'Download file is corrupt. Expected {total_size} bytes, got {file_size}')

def create_filter_array(array, filter_true, filter_false):
    filter_arr = []
    for element in array:
        if element in filter_true:
            filter_arr.append(0)
        if element in filter_false:
            filter_arr.append(1)
    return filter_arr

def smooth_timeseries(ts, method='savitsky', window_length=3, polyorder=1):
    if (method=='savitsky'):
        smooth_ts = savgol_filter(x=ts, window_length=window_length, polyorder=polyorder)
    return smooth_ts

def get_timeseries_datacube(cube, geom):
    band_ts = cube.sel(x=geom[0]['coordinates'][0], y=geom[0]['coordinates'][1], method='nearest')['band_data'].values
    timeline = cube.coords['time'].values
    ts = []
    for value in band_ts:
        ts.append(value[0])
    return dict(values=ts, timeline= timeline)

def unzip():
    for z in glob.glob("*.zip"):
        try:
            with zipfile.ZipFile(os.path.join(z), 'r') as zip_ref:
                #print('Unziping '+ z)
                zip_ref.extractall('unzip')
                os.remove(z)
        except:
            #print("An exception occurred")
            os.remove(z)
            
def geometry_collides_with_bbox(geometry,input_bbox):
    """
    Check if a Shapely geometry collides with a bounding box.
    
    Args:
        geometry: A Shapely geometry object (Polygon, LineString, Point, etc.)
        bbox: A tuple in (minx, miny, maxx, maxy) format
        
    Returns:
        bool: True if the geometry intersects with the bbox, False otherwise
    """
    # Create a Polygon from the bbox
    bbox_polygon = box(*input_bbox)
    
    # Check for intersection
    return geometry.intersects(bbox_polygon)
     
def filter_scenes(collection, data_dir, bbox):
    """
    Return scenes from data_dir where the geometry collides with the bounding box.
    
    Args:
        collection: A string with BDC collection id
        data_dir: A string with directory
        bbox: A tuple in (minx, miny, maxx, maxy) format
        
    Returns:
        list: Scenes filtered by when geometry collides with the bounding box.
    """
    
    # Collection Metadata
    collection_metadata = load(open(os.path.join(data_dir, collection, str(collection+".json")), 'r', encoding='utf-8'))
    
    list_dir = [item for item in os.listdir(os.path.join(data_dir, collection))
            if os.path.isdir(os.path.join(data_dir, collection, item))]
    
    filtered_list = []
    
    for scene in list_dir:
        try:
            item = [item for item in collection_metadata['geoms'] if item["tile"] == scene]
            if (geometry_collides_with_bbox(shape(item[0]['geometry']), bbox)):
                filtered_list.append(item[0]['tile'])   
        except:
            pass
        
    return filtered_list

def local_simple_cube(collection, data_dir, source, bands, tile, bbox):
    
    band = bands[0]
    
    bbox = tuple(map(float, bbox.split(',')))
    
    sample_image_path = os.path.join(data_dir, collection, tile, band)
   
    list_dir = [item for item in os.listdir(sample_image_path)]       
    with rasterio.open(os.path.join(sample_image_path, list_dir[0])) as src:
        data_proj = src.crs
    
    proj_converter = Transformer.from_crs(pyproj.CRS.from_epsg(4326), data_proj, always_xy=True).transform

    bbox_polygon = box(*bbox)
    reproj_bbox = transform(proj_converter, bbox_polygon)
    
    list_da = []
    for image in os.listdir(os.path.join(data_dir, collection, tile, band)):
        da = xr.open_dataarray(os.path.join(data_dir, collection, tile, band, image), engine='rasterio')
        try:
            da = da.rio.clip_box(*reproj_bbox.bounds)  
            if (source == 'bdc'):
                time = image.split("_")[-2]
                dt = datetime.strptime(time, '%Y%m%d') 
            if (source == 'bdc-amz'):
                time = image.split("_")[3]
                dt = datetime.strptime(time, '%Y%m%d') 
            if (source == 'esa'):
                time = image.split("_")[2].split('T')[0]
                dt = datetime.strptime(time, '%Y%m%d')
            if (source == 'nasa'):
                time = image.split(".")[3]
                dt = datetime.strptime(time, '%Y%jT%H%M%S')
            dt = pd.to_datetime(dt)
            da = da.assign_coords(time = dt)
            da = da.expand_dims(dim="time")
            list_da.append(da)
        except:
            pass
    data_cube = xr.combine_by_coords(list_da)   
    return data_cube
       
def name_band(collection, band_id):
    standardized_name = collection.lower().replace('_', '-')
    code = standardized_name.upper().split('-')[0]
    return bands_dict[code][band_id]['name']

def simple_cube_download(data_dir, collection, start_date, end_date, tile=None, bbox=None, freq=None, bands=None):
    
    collection=dict(
        collection=collection, 
        start_date=start_date,
        end_date=end_date,    
        bbox=bbox,
        bands=bands
    )
    
    if collection['collection'] not in ['landsat-2', 'LANDSAT-16D-1', 'S2-16D-2', 'S2_L2A-1']:
        return print(f"{collection['collection']} collection not yet supported.")
    
    collection_get_data(collection, data_dir)
                
    bbox = tuple(map(float, collection['bbox'].split(',')))
    
    scenes = filter_scenes(collection['collection'], data_dir, bbox)
    
    sample_image_path = os.path.join(data_dir, collection['collection'], scenes[0], bands[0])
   
    list_dir = [item for item in os.listdir(sample_image_path)]       
    with rasterio.open(os.path.join(sample_image_path, list_dir[0])) as src:
        data_proj = src.crs
    
    proj_converter = Transformer.from_crs(pyproj.CRS.from_epsg(4326), data_proj, always_xy=True).transform

    bbox_polygon = box(*bbox)
    reproj_bbox = transform(proj_converter, bbox_polygon)
    
    list_da = []
    for i in range(len(bands)):
        for image in os.listdir(os.path.join(data_dir, collection['collection'], scenes[0], bands[i])):
            da = xr.open_dataarray(os.path.join(data_dir, collection['collection'], scenes[0], bands[i], image), engine='rasterio')
            da = da.astype('int16')
            try:
                da = da.rio.clip_box(*reproj_bbox.bounds)  
                if (collection['collection'] == "AMZ1-WFI-L4-SR-1"):
                    time = image.split("_")[3]
                    dt = datetime.strptime(time, '%Y%m%d') 
                if (collection['collection'] == "S2_L2A-1"):
                    time = image.split("_")[2].split('T')[0]
                    dt = datetime.strptime(time, '%Y%m%d')
                if (collection['collection'] == "S2-16D-2"):
                    time = image.split("_")[3]
                    dt = datetime.strptime(time, '%Y%m%d')
                if (collection['collection'] == "LANDSAT-16D-1" or "landsat-2"):
                    time = image.split("_")[3]
                    dt = datetime.strptime(time, '%Y%m%d')
                else:
                    time = image.split("_")[-2]
                    dt = datetime.strptime(time, '%Y%m%d') 
                dt = pd.to_datetime(dt)
                da = da.assign_coords(time = dt)
                da = da.expand_dims(dim="time")
                list_da.append(da)
            except:
                pass
        if (i==0):
            data_cube = xr.combine_by_coords(list_da)
            data_cube = data_cube.rename({'band_data': name_band(collection['collection'], bands[i])})
        else:
            band_data_array = xr.combine_by_coords(list_da)
            band_data_array = band_data_array.rename({'band_data': name_band(collection['collection'], bands[i])})
            data_cube = xr.merge([data_cube, band_data_array])

    return data_cube
       
def interpolate_array(array):
    if len(array) == 0:
        return []
    array = np.array([np.nan if item == -9999 else item for item in array])
    inds = np.arange(len(array))
    good = np.where(np.isfinite(array))
    f = scipy_interpolate.interp1d(inds[good],array[good],bounds_error=False)
    return_array = np.where(np.isfinite(array),array,f(inds))
    return return_array.tolist()

def collection_get_list(datacube):

    collection = datacube['collection']
    bbox = datacube['bbox']
    start_date = datacube['start_date']
    end_date = datacube['end_date']
    bands = datacube['bands'] 

    if (datacube['bbox']):
        item_search = stac.search(
            collections=[collection],
            datetime=start_date+"T00:00:00Z/"+end_date+"T23:59:00Z",
            bbox=bbox
        )
        
    band_dict = {}
    for band in bands:
        band_dict[band] = []

    for item in tqdm(desc='Fetching... ', unit=" scenes", total=item_search.matched(), iterable=item_search.items()):
        for band in bands:
            asset = item.assets.get(band)
            if asset and hasattr(asset, 'href'):
                band_dict[band].append(asset.href)

    return band_dict
  
def collection_get_data(datacube, data_dir):
    
    collection = datacube['collection']
    bbox = datacube['bbox']
    start_date = datacube['start_date']
    end_date = datacube['end_date']
    bands = datacube['bands'] #+ [cloud_dict[collection]['cloud_band']]

    if (datacube['bbox']):
        item_search = stac.search(
            collections=[collection],
            datetime=start_date+"T00:00:00Z/"+end_date+"T23:59:00Z",
            bbox=bbox
        )
        
    tiles = []
    for item in item_search.items():
        if (collection=="AMZ1-WFI-L4-SR-1"):
            tile = item.id.split("_")[4]+'_'+item.id.split("_")[5]
            if tile not in tiles:
                tiles.append(tile)
        if (collection=="S2_L2A-1"):
            tile = item.id.split("_")[5][1:]
            if tile not in tiles:
                tiles.append(tile)
        if (collection=="LANDSAT-16D-1" or "landsat-2" or "S2-16D-2"):
            tile = item.id.split("_")[2]
            if tile not in tiles:
                tiles.append(tile)
                
    for tile in tiles:
        #print(data_dir+"/"+collection+"/"+tile)      
        if not os.path.exists(data_dir+"/"+collection+"/"+tile):
            os.makedirs(data_dir+"/"+collection+"/"+tile)
        for band in bands:
            if not os.path.exists(data_dir+"/"+collection+"/"+tile+"/"+band):
                os.makedirs(data_dir+"/"+collection+"/"+tile+"/"+band)

    geom_map = []
    download = False

    for item in tqdm(desc='Downloading... ', unit=" scenes", total=item_search.matched(), iterable=item_search.items()):
        for band in bands:
            if (collection=="AMZ1-WFI-L4-SR-1"):
                tile = item.id.split("_")[4]+'_'+item.id.split("_")[5]
            if (collection=="S2_L2A-1"):
                tile = item.id.split("_")[5][1:]
            if (collection=="LANDSAT-16D-1" or "landsat-2" or "S2-16D-2"):
                tile = item.id.split("_")[2]

            response = requests.get(item.assets[band].href, stream=True)
            if not any(tile_dict["tile"] == tile for tile_dict in geom_map):
                geom_map.append(dict(tile=tile, geometry=item.geometry))
            if(os.path.exists(os.path.join(data_dir+"/"+collection+"/"+tile+"/"+band, os.path.basename(item.assets[band].href)))):
                download = False
            else:
                download = True
                download_stream(os.path.join(data_dir+"/"+collection+"/"+tile+"/"+band, os.path.basename(item.assets[band].href)), response, total_size=item.to_dict()['assets'][band]["bdc:size"])
    
    if(download):
        file_name = collection+".json"
        with open(os.path.join(data_dir+"/"+collection+"/"+file_name), 'w') as json_file:
            json.dump(dict(collection=collection, geoms=geom_map), json_file, indent=4)

    print(f"Successfully download {item_search.matched()} scenes to {os.path.join(collection)}")

def simple_cube(collection, start_date, end_date, tile=None, bbox=None, freq=None, bands=None):
    
    collection=dict(
        collection=collection, 
        start_date=start_date,
        end_date=end_date,    
        bbox=bbox,
        bands=bands
    )
    
    if collection['collection'] not in ['landsat-2', 'LANDSAT-16D-1', 'S2-16D-2', 'S2_L2A-1', 'samet_daily-1']:
        return print(f"{collection['collection']} collection not yet supported.")
    
    bands_dict = collection_get_list(collection)
                
    bbox = tuple(map(float, collection['bbox'].split(',')))
    
    sample_image_path = bands_dict[bands[0]][0]
      
    with rasterio.open(sample_image_path) as src:
        data_proj = src.crs
    
    proj_converter = Transformer.from_crs(pyproj.CRS.from_epsg(4326), data_proj, always_xy=True).transform

    bbox_polygon = box(*bbox)
    reproj_bbox = transform(proj_converter, bbox_polygon)
    
    list_da = []
    for i in range(len(bands)):
        for image in bands_dict[bands[i]]:
            da = xr.open_dataarray(image, engine='rasterio')
            da = da.astype('int16')
            try:
                da = da.rio.clip_box(*reproj_bbox.bounds)  
                image = image.split('/')[-1]
                if (collection['collection'] == "AMZ1-WFI-L4-SR-1" or "S2-16D-2" or "samet_daily-1" or "LANDSAT-16D-1" or "landsat-2"):
                    time = image.split("_")[3]
                    dt = datetime.strptime(time, '%Y%m%d') 
                if (collection['collection'] == "S2_L2A-1"):
                    time = image.split("_")[2].split('T')[0]
                    dt = datetime.strptime(time, '%Y%m%d')
                else:
                    time = image.split("_")[-2]
                    dt = datetime.strptime(time, '%Y%m%d') 
                dt = pd.to_datetime(dt)
                da = da.assign_coords(time = dt)
                da = da.expand_dims(dim="time")
                list_da.append(da)
            except:
                pass
        if (i==0):
            data_cube = xr.combine_by_coords(list_da)
            data_cube = data_cube.rename({'band_data': name_band(collection['collection'], bands[i])})
        else:
            band_data_array = xr.combine_by_coords(list_da)
            band_data_array = band_data_array.rename({'band_data': name_band(collection['collection'], bands[i])})
            data_cube = xr.merge([data_cube, band_data_array])

    return data_cube