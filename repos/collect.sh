owners=(
  astropy
  django
  matplotlib
  pylint-dev
  pytest-dev
  psf
  scikit-learn
  mwaskom
  sphinx-doc
  pydata
)
repos=(
  astropy
  django
  matplotlib
  pylint
  pytest
  requests
  scikit-learn
  seaborn
  sphinx
  xarray
)

for i in "${!owners[@]}"; do
  git clone "https://github.com/${owners[$i]}/${repos[$i]}.git"
done
