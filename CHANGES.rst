..
    This file is part of Python simplecube package.
    Copyright (C) 2024 INPE.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <https://www.gnu.org/licenses/gpl-3.0.html>.


Changes
=======


0.6.0 (2025-10-14)
------------------

* **NetCDF Support**: The ``simplecube`` function can now create data cubes directly from NetCDF files.
* **GRIB2 Support**: The ``simplecube`` function can now create data cubes directly from GRIB2 files.
* **SAMeT Daily**: Added full support for SAMeT Daily data. 🛰️
* **Function Update**: Updated the ``get_timeseries_datacube`` function to align with new NetCDF and remote file capabilities.
* **MERGE Daily**: Added full support for MERGE Daily Precipitation data. 🛰️
* **New Notebooks**: Added several example notebooks:
    * ``simplecube_s2_rgb.ipynb``: An example for creating a RGB Sentinel-2 data cube.
    * ``simplecube_s2_interpolate.ipynb``: An example for creating a Sentinel-2 cloud interpolate data cube.
    * ``simplecube_s2_smoothed.ipynb``: An example for creating a Sentinel-2  data cube.
    * ``simplecube_s2_spectral_indices.ipynb``: An example for creating a Sentinel-2  data cube and calculating NDVI, EVI2, NDWI and SAVI spectral indices.


0.5.0 (2025-09-25)
------------------

* **Multi-band Support**: It is now possible to create an ``xarray`` data cube with more than one band.
* **COG Support**: Added support for reading Cloud Optimized GeoTIFFs (COGs) with RasterIO, allowing data cube creation without downloading the images. 🛰️
* **New Function**: Added ``simple_cube_download``, which preserves the previous version's behavior of downloading scenes locally.
* **Optimization**: Band data is now automatically cast to ``Int16`` to reduce memory usage.


0.4.0 (2025-07-16)
------------------

* **Landsat Collection 2**: Added full support for Landsat Collection 2 data.
* **New Notebooks**: Added several example notebooks:
    * ``phenometrics_simplecube_s2.ipynb``: A complete example of creating a Sentinel-2 data cube and calculating phenometrics.
    * ``simplecube_hls.ipynb``: An example for creating an HLS data cube.
    * ``simplecube_lc2.ipynb``: An example for creating a Landsat Collection 2 data cube.
    * ``simplecube_s2.ipynb``: An example for creating a Sentinel-2 data cube.


0.3.0 (2025-06-09)
------------------

* **New Function**: Added the new ``local_simple_cube`` function for improved local cube generation.
* **Data Fetching**: Released a new version of ``collection_get_data``.
* **Clipping**: Implemented the ``clip_box`` feature to crop data based on a bounding box in ``simple_cube``.


0.2.0 (2025-06-05)
------------------

* Added the ``cube_get_data`` function.
* Added filtering capabilities to ``simple_cube``.


0.1.0 (2025-05-14)
------------------

* **Initial Release**: First implementation of ``simple_cube`` and ``local_simple_cube`` functions.
* Completed the simplecube introduction notebook.
* Completed the HLS time series example notebook.