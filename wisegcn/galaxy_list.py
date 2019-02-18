import healpy as hp
import numpy as np
from scipy.stats import norm
from scipy.special import gammaincinv
from scipy.special import gammaincc
from configparser import ConfigParser
from wisegcn.email_alert import send_mail
from wisegcn import magnitudes as mag
from wisegcn import mysql_update

# settings:
config = ConfigParser(inline_comment_prefixes=';')
config.read('config.ini')
cat_file = config.get('CATALOG', 'PATH')+config.get('CATALOG', 'NAME')+'.npy'  # galaxy catalog file

# parameters:
credzone = config.getfloat('GALAXIES', 'CREDZONE')
nsigmas_in_d = config.getfloat('GALAXIES', 'NSIGMAS_IN_D')
completenessp = config.getfloat('GALAXIES', 'COMPLETENESS')
minGalaxies = config.getfloat('GALAXIES', 'MINGALAXIES')
ngalaxtoshow = config.getfloat('GALAXIES', 'MAXGALAXIES')  # SET NO. OF BEST GALAXIES TO USE

# magnitude of event in r-band. values are value from barnes... +-1.5 mag
minmag = config.getfloat('GALAXIES', 'MINMAG')
maxmag = config.getfloat('GALAXIES', 'MAXMAG')
sensitivity = config.getfloat('GALAXIES', 'SENSITIVITY')

mindistFactor = config.getfloat('GALAXIES', 'MINDISTFACTOR')  # reflecting a small chance that the theory is completely wrong and we can still see something

minL = mag.f_nu_from_magAB(minmag)
maxL = mag.f_nu_from_magAB(maxmag)

# Schecter function parameters:
alpha = config.getfloat('GALAXIES', 'ALPHA')
MB_star = config.getfloat('GALAXIES', 'MB_STAR')  # random slide from https://www.astro.umd.edu/~richard/ASTRO620/LumFunction-pp.pdf but not really...?

def find_galaxy_list(skymap_path, completeness = completenessp, credzone = 0.99):
    # Read the HEALPix sky map:
    try:
        prob, distmu, distsigma, distnorm = hp.read_map(skymap_path, field=None, verbose=False)
    except Exception as e:
        print('Failed to read sky map!')
        try:
            send_mail(subject="[GW@Wise] Failed to read LVC sky map",
                      text='''FITS file: {}
                              Exception: {}'''.format(skymap_path, e))
        except:
            print('Failed to send email!')
            pass
        return

    # loading the galaxy catalog. this one contains only glade_id, RA, DEC, distance, Bmag
    galax = np.load(cat_file)

    # map parameters:
    npix = len(prob)
    nside = hp.npix2nside(npix)

    # galaxy parameters(RA, DEC to theta, phi):
    galax = (galax[np.where(galax[:, 3] > 0), :])[0]  # no distance<0

    theta = 0.5 * np.pi - np.pi*(galax[:, 2])/180
    phi = np.deg2rad(galax[:, 1])
    d = np.array(galax[:, 3])

    # converting galaxy coordinates to map pixels:
    ipix = hp.ang2pix(nside, theta, phi)

    maxprobcoord_tup = hp.pix2ang(nside, np.argmax(prob))
    maxprobcoord = [0, 0]
    maxprobcoord[0] = np.rad2deg(0.5*np.pi-maxprobcoord_tup[0])
    maxprobcoord[1] = np.rad2deg(maxprobcoord_tup[1])

    # finding given percent probability zone(default is 99%):

    probcutoff = 1
    probsum = 0
    npix99 = 0

    sortedprob = np.sort(prob)
    while probsum<credzone:
        probsum = probsum+sortedprob[-1]
        probcutoff = sortedprob[-1]
        sortedprob = sortedprob[:-1]
        npix99 = npix99+1

    area = npix99 * hp.nside2pixarea(nside, degrees=True)

    ####################################################

    # calculating probability for galaxies by the localization map:
    p = prob[ipix]
    distp = (norm(distmu[ipix], distsigma[ipix]).pdf(d) * distnorm[ipix])# * d**2)#/(norm(distmu[ipix], distsigma[ipix]).pdf(distmu[ipix]) * distnorm[ipix] * distmu[ipix]**2)

    # cuttoffs- 99% of probability by angles and 3sigma by distance:
    inddistance = np.where(np.abs(d-distmu[ipix]) < nsigmas_in_d*distsigma[ipix])
    indcredzone = np.where(p>=probcutoff)

    doMassCuttoff = True


    # if no galaxies
    if (galax[np.intersect1d(indcredzone, inddistance)]).size == 0:
        while probsum < 0.99995:
            if sortedprob.size == 0:
                break
            probsum = probsum + sortedprob[-1]
            probcutoff = sortedprob[-1]
            sortedprob = sortedprob[:-1]
            npix99 = npix99 + 1
        inddistance = np.where(np.abs(d - distmu[ipix]) < 5 * distsigma[ipix])
        indcredzone = np.where(p >= probcutoff)
        doMassCuttoff = False

    ipix = ipix[np.intersect1d(indcredzone, inddistance)]
    p = p[np.intersect1d(indcredzone, inddistance)]
    p = (p * (distp[np.intersect1d(indcredzone, inddistance)]))  ## d**2?

    galax = galax[np.intersect1d(indcredzone, inddistance)]
    if galax.size == 0:
        print("no galaxies in field")
        print("99.995% of probability is ", npix99*hp.nside2pixarea(nside, degrees=True), "deg^2")
        print("peaking at [RA,DEC](deg) = ", maxprobcoord)
        return

    # normalized luminosity to account for mass:
    luminosity = mag.L_nu_from_magAB(galax[:, 4] - 5 * np.log10(galax[:, 3] * (10 ** 5)))
    luminosityNorm = luminosity / np.sum(luminosity)
    luminositynormalization = np.sum(luminosity)
    normalization = np.sum(p * luminosityNorm)

    # taking 50% of mass (missing piece is the area under the Schecter function between l=inf and the brightest galaxy
    # in the field.
    # if the brightest galaxy in the field is fainter than the Schecter function cutoff- no cutoff is made.
    # while the number of galaxies in the field is smaller than minGalaxies- we allow for fainter galaxies,
    # until we take all of them.

    missingpiece = gammaincc(alpha + 2, 10 ** (-(min(galax[:, 4]-5*np.log10(galax[:, 3]*(10**5))) - MB_star) / 2.5))  # no galaxies brighter than this in the field- so don't count that part of the Schechter function

    while doMassCuttoff:
        MB_max = MB_star + 2.5 * np.log10(gammaincinv(alpha + 2, completeness+missingpiece))

        if (min(galax[:, 4]-5*np.log10(galax[:, 3]*(10**5))) - MB_star) > 0:  # if the brightest galaxy in the field is fainter then cutoff brightness- don't cut by brightness
            MB_max = 100

        brightest = np.where(galax[:, 4]-5*np.log10(galax[:, 3]*(10**5)) < MB_max)
        # print MB_max
        if len(brightest[0]) < minGalaxies:
            if completeness >= 0.9:  # tried hard enough. just take all of them
                completeness = 1  # just to be consistent.
                doMassCuttoff = False
            else:
                completeness = (completeness + (1. - completeness) / 2)
        else:  # got enough galaxies
            galax = galax[brightest]
            p = p[brightest]
            luminosityNorm = luminosityNorm[brightest]
            doMassCuttoff = False

    # accounting for distance
    absolute_sensitivity = sensitivity - 5 * np.log10(galax[:, 3] * (10 ** 5))

    absolute_sensitivity_lum = mag.f_nu_from_magAB(absolute_sensitivity)
    distanceFactor = np.zeros(galax.shape[0])

    distanceFactor[:] = ((maxL - absolute_sensitivity_lum) / (maxL - minL))
    distanceFactor[mindistFactor>(maxL - absolute_sensitivity_lum) / (maxL - minL)] = mindistFactor
    distanceFactor[absolute_sensitivity_lum<minL] = 1
    distanceFactor[absolute_sensitivity>maxL] = mindistFactor

    # sorting galaxies by probability
    ii = np.argsort(p*luminosityNorm*distanceFactor)[::-1]

    #### counting galaxies that constitute 50% of the probability(~0.5*0.98)
    sum = 0
    galaxies50per = 0
    observable50per = 0  # how many of the galaxies in the top 50% of probability are observable.
    sum_seen = 0
    enough = True
    while sum < 0.5:
        if galaxies50per >= len(ii):
            enough = False
            break
        sum = sum + (p[ii[galaxies50per]]*luminosityNorm[ii[galaxies50per]])/float(normalization)
        sum_seen = sum_seen + (p[ii[galaxies50per]]*luminosityNorm[ii[galaxies50per]]*distanceFactor[ii[galaxies50per]])/float(normalization)
        galaxies50per = galaxies50per+1

    # event stats:
    #
    # Ngalaxies_50percent = number of galaxies consisting 50% of probability (including luminosity but not distance factor)
    # actual_percentage = usually around 50
    # seen_percentage = if we include the distance factor- how much are the same galaxies worth
    # 99percent_area = area of map in [deg^2] consisting 99% (using only the map from LIGO)
    stats = {"Ngalaxies_50percent": galaxies50per, "actual_percentage": sum*100, "seen_percentage": sum_seen, "99percent_area": area}

    if len(ii) > ngalaxtoshow:
        n = ngalaxtoshow
    else:
        n = len(ii)

    # creating sorted galaxy list, containing info. each entry is (glade_id, RA, DEC, distance(Mpc), Bmag, score, distance factor(between 0-1))
    # score is normalized so that all the galaxies in the field sum to 1 (before luminosity cutoff)
    galaxylist = np.ndarray((ngalaxtoshow, 7))

    # adding to galaxy table database
    for i in range(ii.shape[0])[:n]:
        ind = ii[i]
        galaxylist[i, :] = [galax[ind, 0], galax[ind, 1], galax[ind, 2], galax[ind, 3], galax[ind, 4],
                            (p * luminosityNorm / normalization)[ind], distanceFactor[ind]]
        lvc_galaxy_dict = {'voeventid': '(SELECT MAX(id) from voevent_lvc)',
                           'score': (p * luminosityNorm / normalization)[ind],
                           'gladeid': galax[ind, 0]}
        mysql_update.insert_values('lvc_galaxies', lvc_galaxy_dict)
    
    return galaxylist  # , stats
