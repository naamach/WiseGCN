from astropy import units as u
from astropy.coordinates import Angle
from astropy.time import Time
from wisegcn.observing_tools import is_night, next_night, is_observable
from configparser import ConfigParser
from schedulertml import rtml
from wisegcn.email_alert import send_mail

config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')


def process_galaxy_list(galaxies, filename='galaxies'):
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
                print("Writing plan for GladeID {:.0f}...".format(galaxies[i, 0]))
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

        rtml_filename = config.get('WISE', 'PATH')+filename+'_'+telescopes[tel]+'.xml'
        rtml.write(root, rtml_filename)

        if nothing_to_observe:
            print("Nothing to observe.")
            try:
                send_mail(subject="[GW@Wise] Nothing to observe",
                          text="Nothing to observe for alert {}.".format(filename))
            except:
                print("Failed to send email!")
                pass
        else:
            print("Created observing plan for alert {}.".format(filename))
            try:
                send_mail(subject="[GW@Wise] {} observing plan".format(telescopes[tel]),
                          text="{} observing plan for alert {}."
                          .format(telescopes[tel], filename),
                          files=[rtml_filename])
            except:
                print("Failed to send email!")
                pass

        #rtml.import_to_scheulder(rtml_filename)
    return
