
# coding: utf-8

# Loading cloud-free Sentinel 2 and Landsat from multiple satellites into one dataset

import os
import sys
import datacube
import numpy as np
import pandas as pd
import xarray as xr
from functools import partial
from datacube.utils import geometry
from datacube.utils.geometry import CRS
from datacube import Datacube
from skimage import exposure
from skimage.color import rgb2hsv, hsv2rgb
from unsharp_mask import unsharp_mask

# Import external functions from dea-notebooks using relative link to Scripts
sys.path.append('../10_Scripts')
import DEAPlotting
import DEADataHandling

# Connect to datacube database
dc = datacube.Datacube(app='Time series animation')


def interpolate_timeseries(ds, freq='7D', method='linear'):
    
    """
    Interpolate new data between each existing xarray timestep at a given
    frequency. For example, `freq='7D'` will interpolate new values at weekly
    intervals from the start time of the xarray dataset to the end time. 
    `freq='24H'` will interpolate new values for each day, etc.
    
    :param ds:
        The xarray dataset to interpolate new time-step observations for.
        
    :param freq:
        An optional string giving the frequency at which to interpolate new time-step 
        observations. Defaults to '7D' which interpolates new values at weekly intervals; 
        for a full list of options refer to Panda's list of offset aliases: 
        https://pandas.pydata.org/pandas-docs/stable/timeseries.html#timeseries-offset-aliases
        
    :param method:
        An optional string giving the interpolation method to use to generate new time-steps.
        Default is 'linear'; options are {'linear', 'nearest'} for multidimensional arrays and
        {'linear', 'nearest', 'zero', 'slinear', 'quadratic', 'cubic'} for 1-dimensional arrays.
        
    :return:
        A matching xarray dataset covering the same time period as `ds`, but with an 
        interpolated for each time-step given by `freq`.
        
    """    
    
    # Use pandas to generate dates from start to end of ds at a given frequency
    start_time = combined_ds.isel(time=0).time.values.item() 
    end_time = combined_ds.isel(time=-1).time.values.item()    
    from_to = pd.date_range(start=start_time, end=end_time, freq=freq)
    
    # Use these dates to linearly interpolate new data for each new date
    print(f'Interpolating {len(from_to)} time-steps at {freq} intervals')
    return ds.interp(coords={'time': from_to})


def hsv_image_processing(rgb_array,
                         hue_mult=1, sat_mult=1.035, val_mult=1.035,
                         unsharp_radius1=20, unsharp_amount1=2.5, 
                         unsharp_radius2=1, unsharp_amount2=1.0):   
    
    # Convert to HSV and multiply bands
    hsv_array = rgb2hsv(rgb_array)
    hsv_array[:, :, 0] = hsv_array[:, :, 0] * hue_mult
    hsv_array[:, :, 1] = hsv_array[:, :, 1] * sat_mult
    hsv_array[:, :, 2] = hsv_array[:, :, 2] * val_mult
    
    # Apply unsharp mask and take average
    a = unsharp_mask(hsv_array[:, :, 2], radius=unsharp_radius1, amount=unsharp_amount1)
    b = unsharp_mask(hsv_array[:, :, 2], radius=unsharp_radius2, amount=unsharp_amount2)
    hsv_array[:, :, 2] = np.mean(np.array([a, b]), axis=0)
    
    # Convert back to RGB
    return hsv2rgb(hsv_array.clip(0, 1))


#############################
# Set up analysis variables #
#############################

# # Channel country
# study_area = 'channelcountry'
# lat, lon, buffer_m = -25.63, 142.449760, 20000
# time_range = ('1986-06-01', '2018-12-01')
# resolution = (-50, 50)
# landsat_clearprop = 0.98
# sentinel_clearprop = 0.8
# landsat_sensors = ['ls5', 'ls7', 'ls8']
# sentinel_sensors = None  # ['s2a', 's2b']
# bands = ['swir1', 'nir', 'green']  # ['red', 'green', 'blue']
# percentile_stretch = [0.005, 0.995]
# width_pixels=1200
# interval = 30
# rolling_median = 13
# interpolation_freq = '12D'
# image_proc_func = hsv_image_processing

# # Canberra
# study_area = 'canberra'
# lat, lon, buffer_m = -35.3082, 149.1244, 18000
# time_range = ('1986-06-01', '2018-12-01')
# resolution = (-25, 25)
# landsat_clearprop = 0.96
# sentinel_clearprop = 0.8
# landsat_sensors = ['ls5', 'ls7', 'ls8']
# sentinel_sensors = None  # ['s2a', 's2b']
# bands = ['red', 'green', 'blue']
# percentile_stretch = [0.01, 0.99]
# width_pixels = 2560
# interval = 100
# rolling_median = 25
# interpolation_freq = None
# image_proc_func = partial(hsv_image_processing, val_mult=1.01,
#                           unsharp_radius1=20, unsharp_amount1=0.3,
#                           unsharp_radius2=1, unsharp_amount2=0)

# # Gungahlin
# study_area = 'gungahlin'
# lat, lon, buffer_m = -35.191608, 149.132524, 7500
# time_range = ('1986-06-01', '2018-12-01')
# resolution = (-25, 25)
# landsat_clearprop = 0.96
# sentinel_clearprop = 0.8
# landsat_sensors = ['ls5', 'ls7', 'ls8']
# sentinel_sensors = None  # ['s2a', 's2b']
# bands = ['red', 'green', 'blue']
# percentile_stretch = [0.005, 0.995]
# width_pixels = 2560
# interval = 80
# rolling_median = 31
# interpolation_freq = None
# image_proc_func = partial(hsv_image_processing, val_mult=1.01,
#                           unsharp_radius1=20, unsharp_amount1=0.4,
#                           unsharp_radius2=1, unsharp_amount2=0)

# Molonglo
study_area = 'molonglo'
lat, lon, buffer_m = -35.307688, 149.032756, 5500
time_range = ('1999-01-01', '2018-12-01')
resolution = (-25, 25)
landsat_clearprop = 0.96
sentinel_clearprop = 0.8
landsat_sensors = ['ls5', 'ls7', 'ls8']
sentinel_sensors = None  # ['s2a', 's2b']
bands = ['red', 'green', 'blue']
percentile_stretch = [0.005, 0.995]
width_pixels = 2560
interval = 120
rolling_median = 7
interpolation_freq = None #'14D'
image_proc_func = partial(hsv_image_processing, val_mult=1.01,
                          unsharp_radius1=20, unsharp_amount1=0.4,
                          unsharp_radius2=1, unsharp_amount2=0)



##############################
# Load in Landsat timeseries #
##############################

# Set up analysis data query using a buffer around a lat-long point (1280 x 720).
# This simply converts a lat long to Australian Albers, then creates a square analysis region
# by creating a square buffer around the point.
x, y = geometry.point(lon, lat, CRS('WGS84')).to_crs(CRS('EPSG:3577')).points[0]
query = {'x': (x - buffer_m * (1280/720.0), x + buffer_m * (1280/720.0)),
         'y': (y - buffer_m, y + buffer_m),    
         'time': time_range,
         'crs': 'EPSG:3577',
         'output_crs': 'EPSG:3577',
         'resolution': resolution} 

# Load cloud free Landsat data for all sensors (LS5, LS7, LS8) for the above query. Setting 
# `satellite_metadata=True` will return the data with a variable that gives the abbreviation
# of the satellite that made the observation
landsat_ds = DEADataHandling.load_clearlandsat(dc=dc, query=query,
                                               sensors=landsat_sensors,
                                               bands_of_interest=bands,
                                               masked_prop=landsat_clearprop, 
                                               mask_pixel_quality=False,
                                               mask_invalid_data=False,
                                               ls7_slc_off=False)

#################################
# Load in Sentinel 2 timeseries #
#################################

if sentinel_sensors:

    # Before Sentinel 2 data can be combined with Landsat, create dicts to rename band names to match Landsat:
    bands_s2_to_ls = {'nbart_red': 'red', 'nbart_green': 'green', 'nbart_blue': 'blue',
                      'nbart_nir_1': 'nir', 'nbart_swir_2': 'swir1'}
    bands_ls_to_s2 = {v: k for k, v in bands_s2_to_ls.items()}

    # Load cloud free Sentinel data for all sensors (S2A, S2B) for the above query.
    sentinel_ds = DEADataHandling.load_clearsentinel2(dc=dc, query=query,
                                                      sensors=sentinel_sensors,
                                                      bands_of_interest=[bands_ls_to_s2[band] for band in bands],
                                                      masked_prop=sentinel_clearprop,
                                                      mask_pixel_quality=False,
                                                      mask_invalid_data=False)

    # Rename bands to match Landsat to allow combining/concatenating
    sentinel_ds.rename(bands_s2_to_ls, inplace=True)


##################################
# Combine Landsat and Sentinel 2 #
##################################

try:

    # Combine into one dataset
    combined_ds = xr.auto_combine([landsat_ds, sentinel_ds])

    # Sort by time
    combined_ds = combined_ds.sortby('time')

except:

    # If no Sentinel, just use Landsat as combined dataset
    combined_ds = landsat_ds


###########
# Animate #
###########

# Optionally apply rolling median
if rolling_median:

    combined_ds = combined_ds.rolling(time=rolling_median, center=True, min_periods=1).median()

# Optionally apply interpolation
if interpolation_freq:

    combined_ds = interpolate_timeseries(combined_ds, freq=interpolation_freq)

# Produce an RGB animation that includes both Sentinel and Landsat observations, using
# the `title` parameter to print satellite names for each observation
DEAPlotting.animated_timeseries(ds=combined_ds,
                                output_path=f'animated_timeseries_{study_area}.mp4',
                                bands=bands,
                                interval=interval,
                                width_pixels=width_pixels,
                                percentile_stretch=percentile_stretch,
                                show_date=False,
                                title=combined_ds.time.dt.year.values.tolist(),
                                image_proc_func=image_proc_func)
