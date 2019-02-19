from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from wisegcn.observing_tools import is_night, next_night, is_observable
from configparser import ConfigParser
from schedulertml import rtml
from wisegcn.email_alert import send_mail

config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')
is_debug = config.getboolean('GENERAL', 'DEBUG') if config.has_option('GENERAL', 'DEBUG') else False


def process_galaxy_list(galaxies, filename='galaxies', ra_event=None, dec_event=None):
    """Get the full galaxy list, and find which are good to observe at Wise"""

    t = Time.now()
    if not is_night(lat=config.getfloat('WISE', 'LAT')*u.deg,
                    lon=config.getfloat('WISE', 'LON')*u.deg,
                    alt=config.getfloat('WISE', 'ALT')*u.m,
                    t=t,
                    sun_alt_twilight=config.getfloat('OBSERVING', 'SUN_ALT_MAX')*u.deg):
        print("Daytime at Wise! Preparing a plan for next sunset.")
        t = next_night(lat=config.getfloat('WISE', 'LAT')*u.deg,
                    lon=config.getfloat('WISE', 'LON')*u.deg,
                    alt=config.getfloat('WISE', 'ALT')*u.m,
                    t=t,
                    sun_alt_twilight=config.getfloat('OBSERVING', 'SUN_ALT_MAX')*u.deg)
    else:
        print("It's nighttime at Wise! Preparing a plan for NOW.")

    telescopes = config.get('WISE', 'TELESCOPES').split(',')

    nothing_to_observe = True
    for tel in range(0, len(telescopes)):
        print("Writing plan for {}".format(telescopes[tel]))
        root = rtml.init(name=config.get('OBSERVING', 'USER'),
                         email=config.get('OBSERVING', 'EMAIL'))

        root = rtml.add_request(root,
                                request_id=filename,
                                bestefforts=config.get('OBSERVING', 'BESTEFFORTS'),
                                user=config.get('OBSERVING', 'USER'),
                                description=config.get('OBSERVING', 'DESCRIPTION'),
                                project=config.get('OBSERVING', 'PROJECT'),
                                airmass_min=config.get(telescopes[tel], 'AIRMASS_MIN'),
                                airmass_max=config.get(telescopes[tel], 'AIRMASS_MAX'),
                                hourangle_min=config.get(telescopes[tel], 'HOURANGLE_MIN'),
                                hourangle_max=config.get(telescopes[tel], 'HOURANGLE_MAX'))

        for i in range(tel, galaxies.shape[0], len(telescopes)):
            print("Checking GladeID {:.0f}".format(galaxies[i, 0]))
            ra = Angle(galaxies[i, 1] * u.deg)
            dec = Angle(galaxies[i, 2] * u.deg)
            is_observe = is_observable(ra=ra, dec=dec, lat=config.getfloat('WISE', 'LAT')*u.deg,
                                       lon=config.getfloat('WISE', 'LON')*u.deg,
                                       alt=config.getfloat('WISE', 'ALT')*u.m,
                                       t=t,
                                       ha_min=config.getfloat(telescopes[tel], 'HOURANGLE_MIN')*u.hourangle,
                                       ha_max=config.getfloat(telescopes[tel], 'HOURANGLE_MAX')*u.hourangle,
                                       airmass_min=config.getfloat(telescopes[tel], 'AIRMASS_MIN'),
                                       airmass_max=config.getfloat(telescopes[tel], 'AIRMASS_MAX'))
            if is_observe:
                nothing_to_observe = False
                print("Writing plan for GladeID {:.0f}: RA {}, Dec {}...".format(galaxies[i, 0],
                                                                                 ra.to_string(unit=u.degree, decimal=True),
                                                                                 dec.to_string(unit=u.degree, decimal=True, alwayssign=True)))
                if is_debug:
                    print(galaxies[i, :])

                rtml.add_target(root,
                                request_id=filename,
                                ra=ra.to_string(unit=u.degree, decimal=True),
                                dec=dec.to_string(unit=u.degree, decimal=True, alwayssign=True),
                                name="GladeID_{:.0f}".format(galaxies[i, 0]))

                rtml.add_picture(root,
                                 filt=config.get(telescopes[tel], 'FILTER'),
                                 target_name="GladeID_{:.0f}".format(galaxies[i, 0]),
                                 exptime=config.get(telescopes[tel], 'EXPTIME'),
                                 binning=config.get(telescopes[tel], 'BINNING'))

        print("Event most probable RA={}, Dec={}.".format(ra_event, dec_event))
        if nothing_to_observe:
            print("Nothing to observe.")
            send_mail(subject="[GW@Wise] Nothing to observe",
                      text="Nothing to observe for alert {}.\n Event most probable RA={}, Dec={}."
                      .format(filename, ra_event, dec_event))

        else:
            rtml_filename = config.get('WISE', 'PATH') + filename + '_' + telescopes[tel] + '.xml'
            rtml.write(root, rtml_filename)

            print("Created observing plan for alert {}.".format(filename))
            send_mail(subject="[GW@Wise] {} observing plan".format(telescopes[tel]),
                      text="{} observing plan for alert {}.\n Event most probable RA={}, Dec={}."
                      .format(telescopes[tel], filename, ra_event, dec_event),
                      files=[rtml_filename])

    return
