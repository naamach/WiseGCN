import gcn.notice_types
from astropy.utils.data import download_file
import shutil
import ntpath
from wisegcn.email_alert import send_mail
from wisegcn import galaxy_list
from wisegcn import wise
from wisegcn import mysql_update
from configparser import ConfigParser
import voeventparse as vp

config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')

alerts_path = config.get('ALERT FILES', 'PATH')  # event alert file path
fits_path = config.get('EVENT FILES', 'PATH')  # event FITS file path
is_test = config.getboolean('GENERAL', 'TEST') if config.has_option('GENERAL', 'TEST') else False


# Function to call every time a GCN is received.
# Run only for notices of type
# LVC_PRELIMINARY, LVC_INITIAL, LVC_UPDATE, or LVC_RETRACTION.
@gcn.handlers.include_notice_types(
    gcn.notice_types.LVC_PRELIMINARY,
    gcn.notice_types.LVC_INITIAL,
    gcn.notice_types.LVC_UPDATE,
    gcn.notice_types.LVC_RETRACTION)
def process_gcn(payload, root):
    # Respond only to 'test'/'observation' events
    if is_test:
        role = 'test'
    else:
        role = 'observation'

    if root.attrib['role'] != role:
        print('Not {}, aborting.'.format(role))
        return

    ivorn = root.attrib['ivorn']
    filename = ntpath.basename(ivorn).split('#')[1]

    # Is retracted?
    if gcn.handlers.get_notice_type(root) == gcn.notice_types.LVC_RETRACTION:
        # Save alert to file
        with open(alerts_path + filename + '.xml', "wb") as f:
            f.write(payload)
        print("Event {} retracted, doing nothing.".format(ivorn))
        send_mail(subject="[GW@Wise] LVC event retracted",
                  text="Attached GCN/LVC retraction {} received, doing nothing.".format(ivorn),
                  files=[alerts_path + filename + '.xml'])
        return

    v = vp.loads(payload)

    # Read all of the VOEvent parameters from the "What" section
    params = {elem.attrib['name']:
              elem.attrib['value']
              for elem in v.iterfind('.//Param')}

    # Respond only to 'CBC' (compact binary coalescence candidates) events.
    # Change 'CBC' to 'Burst' to respond to only unmodeled burst events.
    if params['Group'] != 'CBC':
        print('Not CBC, aborting.')
        return

    # Save alert to file
    with open(alerts_path+filename+'.xml', "wb") as f:
        f.write(payload)
    print("GCN/LVC alert {} received, started processing.".format(ivorn))

    # Read VOEvent attributes
    keylist = ['ivorn', 'role', 'version']
    for key in keylist:
        params[key] = v.attrib[key]

    # Read Who
    params['author_ivorn'] = v.Who.Author.contactName
    params['date_ivorn'] = v.Who.Date

    # Read WhereWhen
    params['observatorylocation_id'] = v.WhereWhen.ObsDataLocation.ObservatoryLocation.attrib['id']
    params['astrocoordsystem_id'] = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoordSystem.attrib['id']
    params['isotime'] = v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Time.TimeInstant.ISOTime

    # Read How
    description = ""
    for item in v.How.iterfind('Description'):
        description = description + ", " + item
    params['how_description'] = description

    # Insert VOEvent to the database
    mysql_update.insert_voevent('voevent_lvc', params)

    # Send alert email
    send_mail(subject="[GW@Wise] LVC alert received",
              text="Attached GCN/LVC alert {} received, started processing.".format(ivorn),
              files=[alerts_path+filename+'.xml'])

    # Download the HEALPix sky map FITS file.
    tmp_path = download_file(params['skymap_fits'])
    skymap_path = fits_path + filename + "_" + ntpath.basename(params['skymap_fits'])
    shutil.move(tmp_path, skymap_path)

    # Create the galaxy list
    galaxies, ra, dec = galaxy_list.find_galaxy_list(skymap_path)

    # Create Wise plan
    wise.process_galaxy_list(galaxies, filename=ivorn.split('/')[-1], ra_event=ra, dec_event=dec)

    print("Done.")
