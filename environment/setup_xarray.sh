#!/bin/bash
set -euxo pipefail

owner='pydata'
repo='xarray'

rm -rf /root/$repo
# pull the repo
git clone https://github.com/$owner/$repo.git /root/$repo
git config --global --add safe.directory "*"
# if you are in china, please set proxy
# set conda proxy
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/r
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/pro
#conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/msys2
#conda config --set show_channel_urls yes
## set pip proxy
#pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

source /opt/miniconda3/etc/profile.d/conda.sh

# 0014 0015 0016
conda create -n xarray_0014 python==3.6 -y && \
conda activate xarray_0014 && \
pip install pip==21.1.2 pytest==7.0.1 bottleneck==1.4.0

# 0017 - 0021
conda create -n xarray_0017 python==3.7 -y && \
conda activate xarray_0017 && \
pip install pytest==7.4.4 cftime==1.6.2 dask==2022.2.0

# 2203 - 2212
conda create -n xarray_2203 python==3.9 -y && \
conda activate xarray_2203 && \
pip install pytest==8.3.5 cftime==1.6.2 pandas==1.3.5 numpy==1.26.0 matplotlib==3.9.4 seaborn==0.13.2 dask==2022.8.1 netCDF4 scipy==1.11.1 zarr==2.18.2 aiobotocore h5netcdf pydap Nio cfgrib PseudoNetCDF rasterio nc_time_axis cartopy bottleneck numexpr scitools-iris numbagg pint sparse

# 2303 - 2312
conda create -n xarray_2303 python==3.9 -y && \
conda activate xarray_2303 && \
pip install pytest numpy==1.22.0 pandas==1.4 cftime dask==2022.8.1 scipy netCDF4 zarr Nio h5netcdf pydap cfgrib PseudoNetCDF rasterio bottleneck sparse numexpr scitools-iris pint dask[dataframe]==2022.8.1 aiobotocore distributed==2022.8.1 hypothesis

# 2401 - 2411
conda create -n xarray_2401 python==3.11 -y && \
conda activate xarray_2401 && \
pip install pytest numpy==1.24 pandas cftime dask==2024.3.0 scipy netCDF4 zarr Nio h5netcdf pydap cfgrib PseudoNetCDF rasterio bottleneck sparse numexpr scitools-iris pint dask[dataframe]==2024.3.0 aiobotocore distributed==2024.3.0 hypothesis array-api-strict
