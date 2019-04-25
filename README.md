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


#### Upgrading
To upgrade `wisegcn` run:
```
$ pip install git+https://github.com/naamach/wisegcn.git --upgrade
```

#### The configuration file

Finally, you will have to provide `wisegcn` with the database credentials and point it to the catalog file and to the directory where you want it to store the event `FITS` files.
To do so, you will need to have a `config.ini` file in the working directory (the directory from which you run the script).
The file should look like that (see `config.ini.example` in the main directory):
```
; config.ini
[GENERAL]
TEST = False ; True - listen ONLY test alerts, change to False to listen to real alerts

[LOG]
PATH = /path/to/log/
CONSOLE_LEVEL = DEBUG ; DEBUG, INFO, WARNING, ERROR, CRITICAL
FILE_LEVEL = DEBUG ; DEBUG, INFO, WARNING, ERROR, CRITICAL

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

[ALERT FILES]
PATH = /path/to/alerts/

[EVENT FILES]
PATH = /path/to/ligoevent_fits/

[GALAXIES]
CREDZONE = 0.99
RELAXED_CREDZONE = 0.99995
NSIGMAS_IN_D = 3
RELAXED_NSIGMAS_IN_D = 5
COMPLETENESS = 0.5
MINGALAXIES = 100
MAXGALAXIES = 500 ; number of best galaxies to use
MAXGALAXIESPLAN = 100 ; maximal number of galaxies per observation plan
MINMAG = -12 ; magnitude of event in r-band
MAXMAG = -17 ; magnitude of event in r-band
SENSITIVITY = 22
MINDISTFACTOR = 0.01 ; reflecting a small chance that the theory is completely wrong and we can still see something
ALPHA = -1.07 ; Schechter function parameters
MB_STAR = -20.7 ; Schechter function parameters, random slide from https://www.astro.umd.edu/~richard/ASTRO620/LumFunction-pp.pdf but not really...?

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

[C18]
AIRMASS_MIN = 1
AIRMASS_MAX = 3
HOURANGLE_MIN = -12
HOURANGLE_MAX = 12
FILTER = Clear
EXPTIME = 300
BINNING = 1
HOST = c18_computer_name

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

To listen and process public events run (while the `gw` `conda` environment is activated):


```
$ wisegcn-listen
```

This will listen for VOEvents until killed with ctrl+C.

Alternativey, from inside `python` run:

```
import gcn
from wisegcn.handler import process_gcn

print("Listening to GCN notices (press Ctrl+C to kill)...")
gcn.listen(handler=process_gcn)
```

### Testing `wisegcn` offline

To test `wisegcn` offline, first download the sample GCN notice:

```
$ curl -O https://emfollow.docs.ligo.org/userguide/_static/MS181101ab-1-Preliminary.xml
```

Then run:

```
$ wisegcn_localtest
```

Alternativey, from inside `python` run (while the `gw` `conda` environment is activated):

```
from wisegcn.handler import process_gcn
import lxml.etree

print("Assuming MS181101ab-1-Preliminary.xml is in the working directory")
filename = 'MS181101ab-1-Preliminary.xml'

payload = open(filename, 'rb').read()
root = lxml.etree.fromstring(payload)
process_gcn(payload, root)
```

## Acknowledgments
Leo P. Singer, Scott Barthelmy, David Guevel, Michael Zalzman, Sergiy Vasylyev.

`wisegcn` is based on [svasyly/pygcn](https://github.com/svasyly/pygcn), which is based on [lpsinger/pygcn](https://github.com/lpsinger/pygcn).
