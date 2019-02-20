from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
from astropy import units as u
from astropy.time import Time
import numpy as np


def is_night(lat, lon, alt, t=Time.now(), sun_alt_twilight=-12*u.deg):
    """is it nighttime?"""

    obs = EarthLocation(lat=lat, lon=lon, height=alt)
    sun_altaz = get_sun(t).transform_to(AltAz(obstime=t, location=obs))
    if sun_altaz.alt > sun_alt_twilight:
        return False

    return True


def next_night(lat, lon, alt, t=Time.now(), sun_alt_twilight=-12*u.deg):
    """when is next night?"""
    obs = EarthLocation(lat=lat, lon=lon, height=alt)
    t_vec = t + np.arange(0, 12*60, 1) * u.minute
    sun_altaz = get_sun(t_vec).transform_to(AltAz(obstime=t_vec, location=obs))
    night_idx = np.argmax(sun_altaz.alt < sun_alt_twilight)
    return t_vec[night_idx]


def calc_airmass(ra, dec, lat, lon, alt, t=Time.now()):
    obs = EarthLocation(lat=lat, lon=lon, height=alt)
    obj = SkyCoord(ra=ra, dec=dec, frame='icrs')
    obj_altaz = obj.transform_to(AltAz(obstime=t, location=obs))
    airmass = obj_altaz.secz
    return airmass


def calc_hourangle(ra, lon, t=Time.now()):
    lst = t.sidereal_time('apparent', lon)
    ha = lst - ra
    return ha


def is_observable(ra, dec, lat, lon, alt, t=Time.now(), ha_min=-4.6*u.hourangle, ha_max=4.6*u.hourangle,
                  airmass_min=1.02, airmass_max=3, return_values=False):
    # is the object visible?
    airmass = calc_airmass(ra, dec, lat, lon, alt, t)
    if airmass <= airmass_min or airmass >= airmass_max:
        if return_values:
            return False, airmass, 0
        else:
            return False

    # is the hour angle within the limits?
    ha = calc_hourangle(ra, lon, t)
    if ha <= ha_min or ha >= ha_max:
        if return_values:
            return False, airmass, np.double(ha)
        else:
            return False

    if return_values:
        return True, airmass, np.double(ha)
    else:
        return True
