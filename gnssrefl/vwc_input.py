import argparse
import numpy as np
import os
import sys

from pathlib import Path

from gnssrefl.gps import l2c_l5_list
from gnssrefl.utils import read_files_in_dir, FileTypes, FileManagement


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("station", help="station name", type=str)
    parser.add_argument("year", help="year", type=int)
    parser.add_argument("-min_tracks", default=None, help="minimum number of tracks needed to keep the mean RH", type=int)
    parser.add_argument("-fr", default=None, help="frequency", type=int)

    args = parser.parse_args().__dict__

    # only return a dictionary of arguments that were added from the user - all other defaults will be set in code below
    return {key: value for key, value in args.items() if value is not None}


def vwc_input(station: str, year: int, fr: int = 20, min_tracks: int = 100 ):
    """
    Starts the analysis for volumetric water content.  
    Picks up reflector height (RH) results for a given station and year-year end range and 
    computes the RH mean values and writes them to a file. These will be used to compute a consistent
    set of phase estimates.

    Parameters
    ----------
    station : string
        4 character ID of the station
    year : integer
        Year
    fr : integer, optional
        GPS frequency. Currently only supports l2c, which is frequency 20.
    min_tracks : integer, optional
        number of minimum tracks needed in order to keep the average RH

    Returns
    -------
    File with columns
    index, mean reflector_heights, satellite, average_azimuth, number of reflector heights in average, min azimuth, max azimuth

    Saves to $REFL_CODE/input/<station>_phaseRH.txt

    """
    # default l2c, but can ask for L1 and L2
    xdir = Path(os.environ["REFL_CODE"])
    myxdir = os.environ['REFL_CODE']

    if (len(station) != 4):
        print('station name must be four characters. Exiting.')
        sys.exit()
    if (len(str(year)) != 4):
        print('Year must be four characters. Exiting.')
        sys.exit()

    # not sure this is needed?
    if not min_tracks:
        min_tracks = 100

    print('Minimum number of tracks required ', min_tracks)
    gnssir_results = []
    # removed the ability to look at multiple years
    # it failed and there is no need for it at this time
    y = year
    data_dir = xdir / str(y) / 'results' / station
    result_files = read_files_in_dir(data_dir)
    if result_files == None:
        print('Exiting.')
        sys.exit()

    gnssir_results = np.asarray(result_files)

    # change it to a numpy array
    #gi = np.asarray(gnssir_results)
    # I transpose this because the original code did that.
    gnssir_results = np.transpose(gnssir_results) 


    # four quadrants
    azimuth_list = [0, 90, 180, 270]

    # get the satellites for the requested frequency (20 for now) and most recent year
    if (fr == 1):
        l1_satellite_list = np.arange(1,33)
        satellite_list = l1_satellite_list
        apriori_path_f = myxdir + '/input/' + station + '_phaseRH_L1.txt'
    else:
        print('Using L2C satellite list for December 31 on ', year)
        l2c_sat, l5_sat = l2c_l5_list(year, 365)
        satellite_list = l2c_sat
        apriori_path_f = myxdir + '/input/' + station + '_phaseRH.txt'


    # window out frequency 20
    # the following function returns the index values where the statement is True
    frequency_indices = np.where(gnssir_results[10] == fr)

    reflector_height_gnssir_results = gnssir_results[2][frequency_indices]
    satellite_gnssir_results = gnssir_results[3][frequency_indices]
    azimuth_gnssir_results = gnssir_results[5][frequency_indices]

    b=0

    apriori_array = []
    for azimuth in azimuth_list:
        azimuth_min = azimuth
        azimuth_max = azimuth + 90
        for satellite in satellite_list:
            reflector_heights = reflector_height_gnssir_results[(azimuth_gnssir_results > azimuth_min)
                                                                & (azimuth_gnssir_results < azimuth_max)
                                                                & (satellite_gnssir_results == satellite)]
            azimuths = azimuth_gnssir_results[(azimuth_gnssir_results > azimuth_min)
                                              & (azimuth_gnssir_results < azimuth_max)
                                              & (satellite_gnssir_results == satellite)]
            if (len(reflector_heights) > min_tracks):
                b = b+1
                average_azimuth = np.mean(azimuths)
                #print("{0:3.0f} {1:5.2f} {2:2.0f} {3:7.2f} {4:3.0f} {5:3.0f} {6:3.0f} ".format(b, np.mean(reflector_heights), satellite, average_azimuth, len(reflector_heights),azimuth_min,azimuth_max))
                apriori_array.append([b, np.mean(reflector_heights), satellite, average_azimuth, len(reflector_heights), azimuth_min, azimuth_max])

    apriori_path = FileManagement(station, FileTypes("apriori_rh_file")).get_file_path()

    # save file

    if (len(apriori_array) == 0):
        print('Found no results - perhaps wrong year? or ')
    else:
        print('>>>> Apriori RH file written to ', apriori_path_f)
        fout = open(apriori_path_f, 'w+')
        fout.write("{0:s}  \n".format('% apriori RH values used for phase estimation'))
        l = '% year/station ' + str(year) + ' ' + station 
        fout.write("{0:s}  \n".format(l))
        fout.write("{0:s}  \n".format('% tmin 0.05 (default)'))
        fout.write("{0:s}  \n".format('% tmax 0.50 (default)'))
        fout.write("{0:s}  \n".format('% Track  RefH SatNu MeanAz  Nval   Azimuths '))
        fout.write("{0:s}  \n".format('%         m   ' ))

    #with open(apriori_path, 'w') as my_file:
        np.savetxt(fout, apriori_array, fmt="%3.0f %6.3f %4.0f %7.2f   %4.0f  %3.0f  %3.0f")
        fout.close()


def main():
    args = parse_arguments()
    vwc_input(**args)


if __name__ == "__main__":
    main()
