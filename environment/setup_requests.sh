#!/bin/bash
set -euxo pipefail

owner='psf'
repo='requests'


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

conda create -n requests_227 python==3.9 -y

conda create -n requests_226 python==3.9 -y && \
conda activate requests_226 && \
pip install attrs==25.3.0 blinker==1.9.0 brotlipy==0.7.0 certifi==2025.1.31 cffi==1.17.1 charset-normalizer==2.0.12 click==7.1.2 coverage==7.8.0 cryptography==43.0.3 decorator==5.2.1 Flask==1.1.4 httpbin==0.7.0 idna==3.10 iniconfig==2.1.0 itsdangerous==1.1.0 Jinja2==2.11.3 MarkupSafe==2.0.1 packaging==24.2 pip==25.0 pluggy==1.5.0 py==1.11.0 pycparser==2.22 PySocks==1.7.1 pytest==6.2.5 pytest-cov==6.1.1 pytest-httpbin==1.0.0 pytest-mock==2.0.0 raven==6.10.0 setuptools==75.8.0 six==1.17.0 toml==0.10.2 tomli==2.2.1 trustme==1.2.1 urllib3==1.26.20 Werkzeug==1.0.1 wheel==0.45.1


# python -m pip install -v --no-use-pep517 --no-build-isolation -e .