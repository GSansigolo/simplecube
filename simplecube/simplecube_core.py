
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
from datetime import datetime
import rasterio
import rioxarray
import calendar

cloud_dict = {
    'S2-16D-2':{
        'cloud_band': 'SCL',
        'non_cloud_values': [4,5,6],
        'cloud_values': [0,1,2,3,7,8,9,10,11]
    }
}

def cube_query(collection, start_date, end_date, freq, band=None):
    """An object that contains the information associated with a collection 
    that can be downloaded or acessed.

    Args:
        collection : String containing a collection id.

        start_date String containing the start date of the associated collection. Following YYYY-MM-DD structure.

        end_date : String containing the start date of the associated collection. Following YYYY-MM-DD structure.

        freq String containing the frequency of images of the associated collection. Following (days)D structure. 

        band : Optional, string containing the band id.
    """

    return dict(
        collection = collection,
        band = band,
        start_date = start_date,
        end_date = end_date,
        freq=freq
    )

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
        disable=not progress,
        initial=offset
    )

    mode = 'a+b' if offset else 'wb'

    # May throw exception for read-only directory
    with response:
        with open(file_path, mode) as stream:
            for chunk in response.iter_content(chunk_size):
                stream.write(chunk)
                progress_bar.update(chunk_size)

    file_size = os.stat(file_path).st_size

    if file_size != total_size:
        os.remove(file_path)
        #print(f'Download file is corrupt. Expected {total_size} bytes, got {file_size}')
     
#def download(collection, start_date, end_date, bbox):
    #stac = Client.open(url_stac)
    #item_search = stac.search(bbox=bbox, collections=[collection],  datetime=start_date+'/'+end_date)
    #if not os.path.exists('zip'):
        #os.makedirs('zip')
    #for item in item_search.items():
        #response = requests.get(item.assets["asset"].href, stream=True)
        #download_stream(os.path.basename(item.assets["asset"].href), response, total_size=item.to_dict()['assets']["asset"]["bdc:size"])

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

def simple_cube(data_dir):
    list_da = []
    for path in os.listdir(data_dir):
        da = xr.open_dataarray(os.path.join(data_dir+path), engine='rasterio')
        time = path.split("_")[-2]
        dt = datetime.strptime(time, '%Y%m%d')
        dt = pd.to_datetime(dt)
        da = da.assign_coords(time = dt)
        da = da.expand_dims(dim="time")
        list_da.append(da)
    data_cube = xr.combine_by_coords(list_da)   
    return data_cube

def hls_simple_cube(data_dir):
    list_da = []
    for path in os.listdir(data_dir):
        da = xr.open_dataarray(os.path.join(data_dir+path), engine='rasterio')
        time = path.split(".")[3]
        dt = datetime.strptime(time, '%Y%jT%H%M%S')
        dt = pd.to_datetime(dt)
        da = da.assign_coords(time = dt)
        da = da.expand_dims(dim="time")
        list_da.append(da)
    data_cube = xr.combine_by_coords(list_da, combine_attrs='drop_conflicts')   
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
