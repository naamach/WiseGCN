from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from wisegcn.observing_tools import is_night, next_sunset, next_sunrise, is_observable_in_interval
from configparser import ConfigParser
from schedulertml import rtml
from wisegcn.email_alert import send_mail
import logging

config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')


def process_galaxy_list(galaxies, filename='galaxies', ra_event=None, dec_event=None, log=None):
    """Get the full galaxy list, and find which are good to observe at Wise"""

    if log is None:
        log = logging.getLogger(__name__)

    log.info("Event most probable RA={}, Dec={}.".format(
        ra_event.to_string(unit=u.hourangle, sep=':', precision=2, pad=True),
        dec_event.to_string(sep=':', precision=2, alwayssign=True, pad=True)))

    t = Time.now()
    if not is_night(lat=config.getfloat('WISE', 'LAT')*u.deg,
                    lon=config.getfloat('WISE', 'LON')*u.deg,
                    alt=config.getfloat('WISE', 'ALT')*u.m,
                    t=t,
                    sun_alt_twilight=config.getfloat('OBSERVING', 'SUN_ALT_MAX')*u.deg):
        log.info("Daytime at Wise! Preparing a plan for next sunset.")
        t = next_sunset(lat=config.getfloat('WISE', 'LAT')*u.deg,
                        lon=config.getfloat('WISE', 'LON')*u.deg,
                        alt=config.getfloat('WISE', 'ALT')*u.m,
                        t=t,
                        sun_alt_twilight=config.getfloat('OBSERVING', 'SUN_ALT_MAX')*u.deg)
    else:
        log.info("It's nighttime at Wise! Preparing a plan for NOW.")

    t_sunrise = next_sunrise(lat=config.getfloat('WISE', 'LAT')*u.deg,
                             lon=config.getfloat('WISE', 'LON')*u.deg,
                             alt=config.getfloat('WISE', 'ALT')*u.m,
                             t=t,
                             sun_alt_twilight=config.getfloat('OBSERVING', 'SUN_ALT_MAX')*u.deg)

    telescopes = config.get('WISE', 'TELESCOPES').split(',')

    nothing_to_observe = True
    for tel in range(0, len(telescopes)):
        log.info("Writing a plan for the {}".format(telescopes[tel]))
        root = rtml.init(name=config.get('OBSERVING', 'USER'),
                         email=config.get('OBSERVING', 'EMAIL'))

        log.debug("Index\tGladeID\tRA\t\tDec\t\tAirmass\tHA\tDist\tBmag\tScore\t\tDist factor")

        for i in range(tel, galaxies.shape[0], len(telescopes)):

            ra = Angle(galaxies[i, 1] * u.deg)
            dec = Angle(galaxies[i, 2] * u.deg)
            is_observe, airmass, ha = is_observable_in_interval(ra=ra, dec=dec, lat=config.getfloat('WISE', 'LAT')*u.deg,
                                                    lon=config.getfloat('WISE', 'LON')*u.deg,
                                                    alt=config.getfloat('WISE', 'ALT')*u.m,
                                                    t=t,
                                                    ha_min=config.getfloat(telescopes[tel], 'HOURANGLE_MIN')*u.hourangle,
                                                    ha_max=config.getfloat(telescopes[tel], 'HOURANGLE_MAX')*u.hourangle,
                                                    airmass_min=config.getfloat(telescopes[tel], 'AIRMASS_MIN'),
                                                    airmass_max=config.getfloat(telescopes[tel], 'AIRMASS_MAX'),
                                                    return_values=True)

            if is_observe:
                nothing_to_observe = False
                log.debug(
                    "{}:\t{:.0f}\t{}\t{}\t{:+.2f}\t{:+.2f}\t{:.2f}\t{:.2f}\t{:.6g}\t\t{:.2f}\t\tadded to plan!".format(
                        i + 1, galaxies[i, 0],
                        ra.to_string(unit=u.hourangle, sep=':', precision=2, pad=True),
                        dec.to_string(sep=':', precision=2, alwayssign=True, pad=True),
                        airmass, ha, galaxies[i, 3], galaxies[i, 4], galaxies[i, 5], galaxies[i, 6]))

                root = rtml.add_request(root,
                                        request_id="GladeID_{:.0f}".format(galaxies[i, 0]),
                                        bestefforts=config.get('OBSERVING', 'BESTEFFORTS'),
                                        user=config.get('OBSERVING', 'USER'),
                                        description=config.get('OBSERVING', 'DESCRIPTION'),
                                        project=config.get('OBSERVING', 'PROJECT'),
                                        airmass_min=config.get(telescopes[tel], 'AIRMASS_MIN'),
                                        airmass_max=config.get(telescopes[tel], 'AIRMASS_MAX'),
                                        hourangle_min=config.get(telescopes[tel], 'HOURANGLE_MIN'),
                                        hourangle_max=config.get(telescopes[tel], 'HOURANGLE_MAX'))

                rtml.add_target(root,
                                request_id="GladeID_{:.0f}".format(galaxies[i, 0]),
                                ra=ra.to_string(unit=u.degree, decimal=True),
                                dec=dec.to_string(unit=u.degree, decimal=True, alwayssign=True),
                                name="GladeID_{:.0f}".format(galaxies[i, 0]))

                rtml.add_picture(root,
                                 filt=config.get(telescopes[tel], 'FILTER'),
                                 target_name="GladeID_{:.0f}".format(galaxies[i, 0]),
                                 exptime=config.get(telescopes[tel], 'EXPTIME'),
                                 binning=config.get(telescopes[tel], 'BINNING'))
            else:
                log.debug(
                    "{}:\t{:.0f}\t{}\t{}\t{:+.2f}\t{:+.2f}\t{:.2f}\t{:.2f}\t{:.6g}\t\t{:.2f}".format(
                        i + 1, galaxies[i, 0],
                        ra.to_string(unit=u.hourangle, sep=':', precision=2, pad=True),
                        dec.to_string(sep=':', precision=2, alwayssign=True, pad=True),
                        airmass, ha, galaxies[i, 3], galaxies[i, 4], galaxies[i, 5], galaxies[i, 6]))

        if nothing_to_observe:
            log.info("Nothing to observe.")
            send_mail(subject="[GW@Wise] Nothing to observe",
                      text="Nothing to observe for alert {}.\nEvent most probable at RA={}, Dec={}."
                      .format(filename,
                              ra_event.to_string(unit=u.hourangle, sep=':', precision=2, pad=True),
                              dec_event.to_string(sep=':', precision=2, alwayssign=True, pad=True)))

        else:
            rtml_filename = config.get('WISE', 'PATH') + filename + '_' + telescopes[tel] + '.xml'
            rtml.write(root, rtml_filename)

            log.info("Created observing plan for alert {}.".format(filename))
            send_mail(subject="[GW@Wise] {} observing plan".format(telescopes[tel]),
                      text="{} observing plan for alert {}.\nEvent most probable at RA={}, Dec={}."
                      .format(telescopes[tel], filename,
                              ra_event.to_string(unit=u.hourangle, sep=':', precision=2, pad=True),
                              dec_event.to_string(sep=':', precision=2, alwayssign=True, pad=True)),
                      files=[rtml_filename])

    return
