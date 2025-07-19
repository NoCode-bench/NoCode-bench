#!/bin/bash
set -euxo pipefail

# In "4.1", "4.2", "4.3", "5.0", "5.1", "5.2", "v5.3", run below cmd before pip install -e .
# pre_install: sed -i 's/requires = \["setuptools",/requires = \["setuptools==68.0.0",/' pyproject.toml
# install: python -m pip install -e .[test] --verbose
# test: pytest --color=no -rA
owner='astropy'
repo='astropy'

#git config --global http.proxy http://127.0.0.1:7893
#git config --global https.proxy http://127.0.0.1:7893

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

# build one to solve version<1.0
# TODO

conda create -n astropy_11 python==3.6 -y && \
conda activate astropy_11 && \
pip install setuptools==57.4.0 && \
pip install numpy==1.16  matplotlib==3.3.4 scipy==1.5.4 pytest==4.0.0 jinja2==2.10.3 cython==3.0.12 pyparsing==2.4.7 scikit-image==0.17.2 h5py==2.7.0 pytest-remotedata hypothesis


conda create -n astropy_30 python==3.8 -y && \
conda activate astropy_30 && \
pip install setuptools==57.4.0 && \
pip install numpy==1.16  matplotlib==3.3.4 scipy==1.5.4 pytest==6.2.5 hypothesis


conda create -n astropy_40 python==3.8 -y && \
conda activate astropy_40 && \
pip install setuptools==57.4.0 && \
pip install numpy==1.19 pytest-openfiles==0.6.0 matplotlib==3.6.3 hypothesis

conda create -n astropy_41 python==3.8 -y && \
conda activate astropy_41 && \
pip install numpy==1.19 setuptools==57.4.0 pytest-openfiles==0.6.0 matplotlib==3.6.3 hypothesis

conda create -n astropy_42 python==3.9 -y && \
conda activate astropy_42 && \
pip install setuptools==57.4.0 && \
pip install numpy==1.22 scipy==1.10 hypothesis

conda create -n astropy_52  python==3.10 -y && \
conda activate astropy_52 && \
pip install numpy==1.24 scipy matplotlib==3.7 bleach jplephem h5py pytz iPython mpmath objgraph s3fs fsspec beautifulsoup4 dask pyarrow fitsio pandas pytest-mpl skyfield hypothesis

