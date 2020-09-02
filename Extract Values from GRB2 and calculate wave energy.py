import pygrib
import numpy as np
import datetime
import pandas as pd
import os

# Variables to extract
variables = ["dp", "hs", "tp"]

#Search Folder, see CURL download file for list of WW3 output files
search_folder = "/mnt/unraid/Oceanographic_Data/Oceanographic_Data/Waves/NOAA_Global_WW3/30-year_Hindcast_Phase2_Download/"

#These
island_centers = "/mnt/unraid/Oceanographic_Data/Oceanographic_Data/Waves/NOAA_Global_WW3/Island_Centers.csv"

print('Extracting Wave Watch 3 Variables')

# Generate year/month list
print(".. Searching directory for Wave Watch 3 Gribs")
def get_dates_from_file_name(location):
    list_all_files = [f for f in os.listdir(location) if os.path.isfile(os.path.join(location, f))]
    list_only_dates = []
    for i in list_all_files:
        try:
            list_only_dates.append(i.split(".")[3])
        except:
            pass
    unique_set_only_dates = set(list_only_dates)
    unique_list_only_dates = list(unique_set_only_dates)
    unique_list_only_dates_cleaned = [x for x in unique_list_only_dates if x.isdigit()]
    unique_list_only_dates_int = list(map(int, unique_list_only_dates_cleaned))
    unique_list_only_dates_int.sort()
    return unique_list_only_dates_int

dates = get_dates_from_file_name(search_folder)
print(".. Total dates found for processing: " + str(len(dates)))

# Generate generic dataframe to hold data in row format
df = pd.DataFrame(columns=['year', 'month', 'day', 'hour', 'variable', 'value', 'lat', 'lon', 'difflat', 'difflon'])

# Load Island Centers
island_centers_data = pd.read_csv(island_centers)
# Convert island centers to 0-360
island_centers_data['Longitude'] = island_centers_data['Longitude'] + 180

for index, row in island_centers_data.iterrows():
    island = row['Island']
    latitude = row['Latitude']
    longitude = row['Longitude']

    print(".... Processing location: " + str(island))

    for date_s in dates:
        for v in variables:
            print("...... Processing date: " + str(date_s) + " & variable: " + v)
            grbs = pygrib.open(search_folder + "multi_reanal.glo_30m_ext." + v + "." + str(date_s) + ".grb2")

            for grb in grbs:

                date = datetime.datetime.strptime(str(grb.dataDate), "%Y%m%d")
                date_time = date + datetime.timedelta(hours = grb['forecastTime'])


                # Extraction based on Brian Baylock's example https://github.com/blaylockbk/pyBKB_v3/blob/master/demo/Nearest_lat-lon_Grid.ipynb
                lats, lons = grb.latlons()
                values = grb.values

                abslat = np.abs(lats - latitude)
                abslon = np.abs(lons - longitude)

                c = np.maximum(abslon, abslat)

                latlon_idx = np.argmin(c)

                value = values.flat[latlon_idx]

                df = df.append({'year': date_time.strftime("%Y"),
                               'month': date_time.strftime("%m"),
                               'day': date_time.strftime("%d"),
                               'hour': date_time.strftime("%H"),
                               'variable': v,
                               'value': value,
                               'lat': latitude,
                               'lon': longitude
                               }, ignore_index=True)

    df_t = df.pivot_table(index=['year', 'month', 'day', 'hour'], columns='variable', values='value', aggfunc=np.min)
    df_t.replace('--', np.nan)

    # Calculate Wave Power
    print("........ Calculating wave power for " + str(island))
    density = 1024.0
    gravity = 9.81 ** 2.0
    E = ((density * gravity) / (64.0 * 3.1415926535))

    # Wave Energy flux in Watts per Metre of wave crest length
    # dependent on significant wave height ^ 2 and period.Ef is in W / m
    df_t['CgE'] = (E * (df_t.hs ** 2.0) * df_t.tp)

    df_t.to_csv(str(island) + '.csv', index=True)

