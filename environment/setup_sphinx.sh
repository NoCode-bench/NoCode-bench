#!/bin/bash
set -euxo pipefail

owner='sphinx-doc'
repo='sphinx'


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


# 2.0 - 2.4
conda create -n sphinx_20 python=3.7 -y && \
conda activate sphinx_20 && \
python -m pip install tox==3.25 tox-current-env==0.0.12 "pluggy<1.0,>=0.12" virtualenv==16.7.12 "markupsafe<=2.0.1"

# 3.0 - 5.2
conda create -n sphinx_30 python=3.7 -y && \
conda activate sphinx_30 && \
python -m pip install tox==3.25 tox-current-env==0.0.12 "pluggy<1.0,>=0.12" virtualenv==16.7.12

# 6.0 - 7.1
conda create -n sphinx_60 python=3.9 -y && \
conda activate sphinx_60 && \
python -m pip install tox==3.25 tox-current-env==0.0.12 "pluggy<2,>=1.5" virtualenv==16.7.12

# 7.2 - 7.4
conda create -n sphinx_72 python=3.9 -y && \
conda activate sphinx_72 && \
python -m pip install tox==4.2.0 tox-current-env==0.0.12 "pluggy<2,>=1.5" virtualenv==20.17.1

# 8.0 - 8.1
conda create -n sphinx_80 python=3.10 -y && \
conda activate sphinx_80 && \
python -m pip install tox==4.2.0 tox-current-env==0.0.12 "pluggy<2,>=1.5" virtualenv==20.17.1
# python -m pip install -v --no-use-pep517 --no-build-isolation -e .

apt-get update && apt-get install -y graphviz