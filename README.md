[![GPL](https://img.shields.io/badge/license-GPL-blue)](https://github.com/ktand/KicadCut/blob/master/LICENSE)
[![Python](https://img.shields.io/badge/language-Python3-orange)](https://www.python.org)

# About

Generate Silhouette Portrait/Cameo stencil cut file from Kicad PCB file.

Based on the work from [SMTCut](https://github.com/GatCode/SMTCut) and [gerber2graphtec](https://github.com/pmonta/gerber2graphtec)

## Setup

The project uses the [kicad_parser](https://github.com/realthunder/kicad_parser). To get this submodule, after checkout this repository, do

```
git submodule update --init --recursive
```

also install

```
pip install PyUsb
```
```
pip install FPDF
```

## Basic usage

### Generate cut file
```
kicadcut <kicad_pcb_file> <layer> >file.out
```

### Send to Silhouette
```
file2silhouette <cutfile>
```

## Requirements on Windows

file2silhouette requires:
- UsbDk to be installed (https://github.com/daynix/UsbDk)
- libusb-1.0.dll to be copied to C:\Windows\System32 (https://libusb.info/)
