# A global gridded dataset of unified onshore and offshore wind resources and power potential


**Changqing Xu**<sup>a,b</sup>, **Tianyu Jia**<sup>a,b,&#42;</sup>, **Jianchuan Qi**<sup>c,&#42;</sup>, **Peng Wang**<sup>d,e,&#42;</sup>, **Xi Chen**<sup>a</sup>, **Siqi Wang**<sup>a</sup>, **Yunzhi Tang**<sup>a</sup>, **Fangyuan Lu**<sup>f</sup>, **Yuqiao Lan**<sup>a,b</sup>, **Bin Zhang**<sup>b,g</sup>, **Bo Wang**<sup>b,g</sup>, **Jing Guo**<sup>h</sup>, **Chuke Chen**<sup>c</sup>, **Nan Li**<sup>i</sup>, **Ming Xu**<sup>i</sup>, **Zhaohua Wang**<sup>a,b,&#42;</sup>

<br>

<small>
<sup>a</sup> School of Economics, Beijing Institute of Technology, Beijing 100081, China.<br>
<sup>b</sup> Digital Economy and Policy Intelligentization Key Laboratory of Ministry of Industry and Information Technology, Beijing 100081, China.<br>
<sup>c</sup> School of Environment, Tsinghua University, Beijing 100084, China.<br>
<sup>d</sup> State Key Laboratory of Regional and Urban Ecology, Institute of Urban Environment, Chinese Academy of Sciences, Xiamen 361021, China.<br>
<sup>e</sup> University of Chinese Academy of Sciences, Beijing 100049, China.<br>
<sup>f</sup> School of Geography and Ocean Science, Nanjing University, Nanjing, China.<br>
<sup>g</sup> School of Management, Beijing Institute of Technology, Beijing 100081, China.<br>
<sup>h</sup> College of Management Science and Engineering, Beijing Information Science & Technology University, Beijing, 102206, P.R. China.<br>
<sup>i</sup> State Key Laboratory of Iron and Steel Industry Environmental Protection, School of Environment, Tsinghua University, Beijing 100084, China.
</small>

<br>
<small>* Corresponding authors.</small><br>
<small>* Email: 3120246164@bit.edu.cn</small>


## Abstract

This repository provides the source code and processing workflow for the manuscript "A global gridded dataset of unified onshore and offshore wind resources and power potential". The code implements a globally consistent framework for assessing onshore and offshore wind resources from 1980 to 2025 using ERA5 atmospheric reanalysis data and harmonized geospatial screening criteria. It supports the generation of hourly capacity factors (CF), capacity density (CD), energy density (ED), technical potential (TP), and developable potential (DP) products at 0.25° spatial resolution.

The workflow integrates wind-speed extrapolation, air-density correction, turbine power-curve conversion, layout-dependent capacity density assumptions, wake-related losses, and additional system efficiency factors. It also applies spatial constraints including land-cover suitability, protected areas, terrain slope, exclusive economic zones, water depth, offshore distance, and sea-ice conditions. Scenario outputs are provided for three turbine spacing configurations and three developable area ratios, enabling uncertainty analysis across resource, technical, and deployment assumptions.


## Project Data & Availability
Due to the size of high-resolution hourly reanalysis data, the raw input files are not hosted in this repository. Users must obtain the raw data from the official sources listed in the table below.


### Data Sources

| Dataset | Source / Link | Variables Used |
| :--- | :--- | :--- |
| **ERA5 Reanalysis** | [ECMWF CDS](https://cds.climate.copernicus.eu/datasets) | `100u`, `100v` (Wind)<br>`sp`, `t2m` (Density) <br> `Land-Sea Mask (LSM)` <br> `Sea ice cover`|
| **MODIS MCD12C1(v061)** | [Land Use and Land Cover](https://www.earthdata.nasa.gov/data/catalog/lpcloud-mcd12c1-061) | Excluded: water (0), evergreen needleleaf forests (1), evergreen broadleaf forests (2), deciduous needleleaf forests (3), deciduous broadleaf forests (4), mixed forests (5), permanent wetlands (11), urban and built-up (13), snow and ice (15)  <br> Retained: closed shrublands (6), open shrublands (7), woody savannas (8), savannas (9), grasslands (10), croplands (12), cropland/natural vegetation mosaics (14), barren or sparsely vegetated (16) |
| **EEZ v12** | [Exclusive Economic Zones](https://www.marineregions.org/) | Assessment restricted to maritime areas within national EEZs (up to 200 nautical miles) |
| **WDPA** | [Protected Areas](https://www.protectedplanet.net/en/thematic-areas/wdpa%20) | Exclusion of all protected areas with designated or established status in the following IUCN categories: Strict Nature Reserve, Wilderness Area, National Park, Natural Monument/Feature, Habitat/Species Management Area, Protected Landscape/Seascape, Protected Area with Sustainable Resource Use, Indigenous and Community Conserved Area, Drinking-Water Protection Zones, Permanent No-Take Fisheries Zones, Military Exclusion Areas, Long-Term Private Conservation Easements |
| **GEBCO Grid** | [GEBCO](https://www.gebco.net/data-products-gridded-bathymetry-data/gebco2025-grid) | Slope / Elevation / Depth / Distance |
| **Global Wind Atlas** | [GWA 4.0](https://data.dtu.dk/articles/dataset/Global_Wind_Atlas_4/28955267) | Spatial distribution validation |
| **ESTON-E** | [European Network of Transmission System Operators for Electricity](https://transparency.entsoe.eu/) | High-frequency time series validation |


## Directory Structure
To ensure the scripts run successfully, please organize your local data directory as follows (using relative paths):
```text
.
├── code/                      # Python scripts
├── figures/                   # Output figures
└── data/                      # Data Storage
    ├── download/              # [Common Step 1] Raw ERA5 Data
    │   ├── u100/
    │   ├── v100/
    │   ├── sp/
    │   └── t2m/
    ├── ancillary/             # Static GIS Data for Masking
    │   ├── LSM/               # [Common Step 2] Land-Sea Mask
    │   ├── MCD121/            # [Onshore] Land Cover
    │   ├── WDPA/              # [Common] Protected Areas
    │   ├── GEBCO/             # [Common] Slope / Elevation / Depth / Distance
    │   ├── EEZ/               # [Offshore] Exclusive Economic Zones
    │   └── Sea_Ice/           # [Offshore] Sea Ice extent
    ├── onshore/               # [Onshore Branch]
    │   ├── wind_rho/          # Processed V100 & Rho
    │   ├── Pwind/
    │   ├── CF/
    │   └── Potential/         # CD / ED / TP / DP
    ├── offshore/              # [Offshore Branch]
    │   ├── wind_rho/          # Processed V100 & Rho
    │   ├── Pwind/
    │   ├── CF/
    │   └── Potential/         # CD / ED / TP / DP
    └── Validation/            # GWA / ESTON-E / Other literatures
```


## Reproduce My Work
All code used to create and process the data in this publication can be reproduced using the provided Python scripts.


### Prerequisites
These scripts require Python 3.8+. You can install the necessary dependencies (including cdsapi for data download) using pip:
```text
pip install numpy xarray pandas netCDF4 scipy matplotlib cartopy rioxarray cdsapi
```

### ERA5 API Configuration
To run the download scripts in Phase 1, you must configure the Climate Data Store (CDS) API client:
1. Register: Create an account at the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu).
2. Get Credentials: Log in and visit your `User Profile` to copy your UID and API Key.
3. Create Config File: Create a file named `.cdsapirc` in your user home directory (Linux/Mac: `~/.cdsapirc`, Windows: `C:\Users\Username\.cdsapirc`) containing:
```text
url: https://cds.climate.copernicus.eu/api/v2
key: {UID}:{API_KEY}
```
