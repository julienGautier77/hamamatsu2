# hamamatsu2
control hamamatsu camera linux or windows
test on ubuntu 24.04.1 with an Orca flash camera

use visu : https://www.github.com/julienGautier77/visu

use dcamapi4 : 'Copyright (C) 2021-2024 Hamamatsu Photonics K.K.' https://www.hamamatsu.com/eu/en/product/cameras/software/driver-software/dcam-sdk4.html


## Install LINUX : 
  Install DCam-API_lite :
  
  https://www.hamamatsu.com/eu/en/product/cameras/software/driver-software/dcam-api-lite-for-linux.html
  
  command line : relative path from root folder of DCAM-API installer : 
  
    path ./api/install.sh usb3
    
    path ./api/runtime/install.sh usb3
    
    ./api/driver/usb/install.sh


    library should be installed in '/usr/local/lib/libdcamapi.so'

## Install WINDOWS 
  Install https://www.hamamatsu.com/eu/en/product/cameras/software/driver-software/dcam-api-for-windows.html
  
  library should be installed in 'dcamapi.dll'
  
## pip install git+ https://www.github.com/julienGautier77/visu


  
