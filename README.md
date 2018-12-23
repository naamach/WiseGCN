# WiseGCN

A GCN/TAN (Gamma-ray Coordinates Network/Transient Astronomy Network) handler for use at the Wise Observatory in case of gravitational-wave alerts.

## Getting started

### Prerequisites

* `miniconda` or `anaconda` with `python 3`
* `mysql`
* `git`

### Installing

Create and activate a `conda` environment (named `gw`) with the necessary modules:
```
$ conda create -p /path/to/gw python=3.7.1
$ source activate /path/to/gw
$ pip install pygcn healpy configparser voevent-parse pymysql lxml
$ pip install git+https://github.com/naamach/schedulertml.git
$ pip install git+https://github.com/naamach/wisegcn.git
```
Setup the `mysql` database according to [these instructions](docs/mysql.md).

#### The configuration file

Finally, you will have to provide `wisegcn` with the database credentials and point it to the catalog file and to the directory where you want it to store the event `FITS` files.
To do so, you will need to have a `config.ini` file in the working directory (the directory from which you run the script).
The file should look like that (see `config.ini.example` in the main directory):
```
; config.ini
[CATALOG]
PATH = /path/to/catalog/
NAME = glade_2.3_RA_Dec

[EMAIL]
FROM = root@example.com
TO = user@example.com
CC = 
BCC = 
SERVER = localhost

[DB]
HOST = localhost
USER = gcn
PASSWD = password
DB = gw
SOCKET = /var/run/mysqld/mysqld.sock

[EVENT FILES]
PATH = /path/to/ligoevent_fits/

[OBSERVING]
SUN_ALT_MAX = -12
BESTEFFORTS = 1
USER = New Observer
EMAIL = user@example.com
PROJECT = GW followup
DESCRIPTION = 
SOLVE = 1

[WISE]
LAT = 30.59583333333333
LON = 34.763333333333335
ALT = 875
UTC_OFFSET = -2
TELESCOPES = C28  ; C28, C18, 1m
PATH = /path/to/plans/

[C28]
AIRMASS_MIN = 1.02  ; the shutter blocks the CCD above 80deg
AIRMASS_MAX = 3
HOURANGLE_MIN = -4.6
HOURANGLE_MAX = 4.6
FILTER = ExoP
EXPTIME = 300
BINNING = 1
HOST = c28_computer_name

[1m]
AIRMASS_MIN = 1
AIRMASS_MAX = 3
HOURANGLE_MIN = -12
HOURANGLE_MAX = 12
FILTER = Clear
EXPTIME = 300
BINNING = 1
HOST = 1m_computer_name
```

NOTE: To find the `mysql` socket, run:
```
$ netstat -ln | grep mysql
```

## Using `wisegcn`

To listen and process public events run:

```
import gcn
from wisegcn.handler import process_gcn

gcn.listen(handler=process_gcn)
```

This will listen for VOEvents until killed with ctrl+C.

### Testing `wisegcn` offline

To test `wisegcn` offline, first download the sample GCN notice and localization map:

```
$ curl -O https://emfollow.docs.ligo.org/userguide/_static/MS181101ab-1-Preliminary.xml
$ curl -O https://emfollow.docs.ligo.org/userguide/_static/bayestar.fits.gz
```

Save the FITS file in the folder specified in the `config.ini` file (EVENT FILES/PATH). Then run:

```
from wisegcn.handler import process_gcn
import lxml.etree

filename = 'MS181101ab-1-Preliminary.xml'

payload = open(filename, 'rb').read()
root = lxml.etree.fromstring(payload)
process_gcn(payload, root)
```

## Acknowledgments
Leo P. Singer, Scott Barthelmy, David Guevel, Michael Zalzman, Sergiy Vasylyev.

`wisegcn` is based on [svasyly/pygcn](https://github.com/svasyly/pygcn), which is based on [lpsinger/pygcn](https://github.com/lpsinger/pygcn).
