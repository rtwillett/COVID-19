import numpy as np
import pandas as pd
import copy

def ts_record_parse(df, var_title = "Value"):
    ts_cols = df.columns[4:] # Collect the names of all the columns named as a date
    ts_long = pd.melt(df, id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], value_vars=ts_cols, var_name='Date',
            value_name=var_title)
    ts_long['Date'] = pd.to_datetime(ts_long.Date)
    ts_long.columns = ["Province", "Country", "Lat", "Lon", "Date", var_title]
    return(ts_long)


country_labs = pd.read_csv('./additional_data/countries_labels.csv')
country_labs.columns = ['Countries', 'Region', 'Lat', 'Lon']

confirmed = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv")
confirmed_long = ts_record_parse(confirmed, 'Confirmed')
confirmed_long["Country"] = confirmed_long.Country.apply(lambda x: x.replace("*", "")) # To remove the * from Taiwan
confirmed_long['tooltip_confirmed'] = confirmed_long.apply(lambda x : x.Country + ": " + str(x.Confirmed), axis=1)

# pd.DataFrame(confirmed_long.Country.unique(), columns=["Countries"]).to_csv("country_list.csv", index=False, header=True)



# deaths = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_19-deaths_global.csv")
# deaths_long = ts_record_parse(deaths, "Deaths")


# recovered = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_19-recovered_global.csv")
# recovered_long = ts_record_parse(recovered, 'Recovered')


# Merging the timeseries data by day and location for COVID-19 confirmed cases, deaths, and recovered cases.
all_countries = confirmed_long#.merge(deaths_long, on=["Province", "Country", "Lat", "Lon", "Date"]).merge(recovered_long, on=["Province", "Country", "Lat", "Lon", "Date"])

# With the group_by sums aggregating data across the countries, need to renew the geocode data. This will drop the old coordinates
all_countries.drop(columns=['Lat', 'Lon'], inplace=True)

# Applying the region label (by continent) to the larger dataset
all_countries = pd.merge(all_countries, country_labs, left_on="Country", right_on="Countries")
all_countries.to_feather("./parsed_data/all_countries_ts.feather")


# SUMMARIZING BY Date
# Summing all of the confirmed cases, deaths, and recovered patients for each day
data_totTime_confirmed = all_countries.groupby("Date")['Confirmed'].sum().reset_index()
# data_totTime_deaths = all_countries.groupby("Date")['Deaths'].sum().reset_index()
# data_totTime_recovered = all_countries.groupby("Date")['Recovered'].sum().reset_index()

all_countries_summary = copy.deepcopy(data_totTime_confirmed)
# all_countries_summary = all_countries_summary.merge(data_totTime_deaths, on='Date').merge(data_totTime_recovered, on='Date')

all_countries_summary.to_feather("./parsed_data/all_countries_summary.feather")


# Summarizing by country
def regional_summarize(df, var, file_name):

    fileout = './parsed_data/' + file_name
#     print(fileout)

    data_tsSum = df.groupby(['Country', 'Date', 'Region', 'Lat', 'Lon'])[var].sum()
    data_tsSum = data_tsSum.reset_index()

    data_tsSum_sort = data_tsSum.set_index("Country").sort_values(by='Date', ascending=True)
    data_tsSum_sort = data_tsSum_sort.reset_index()
    data_tsSum_sort['tooltip_confirmed'] = data_tsSum_sort.apply(lambda x : x.Country + ": " + str(x.Confirmed), axis=1)

    data_tsSum_sort.to_feather(fileout)

    return(data_tsSum_sort)

def calc_newCases(df, country):
    df_filt = df.loc[df.Country == country]

    if df_filt.shape[0] < 2:
        pass
    else:
        confirmed = df_filt.Confirmed.to_list()

        new_cases=[]
        for i in list(range(len(confirmed)-1)):
            new_cases.append(confirmed[i+1] - confirmed[i])
#             print(confirmed[i+1] - confirmed[i])

        df_out = df_filt.iloc[1:,:].copy()
        df_out['new_cases'] = new_cases
        df_out['tooltip_newcases'] = df_out.apply(lambda x : x.Country + ": " + str(x.new_cases), axis=1)

        return(df_out[['Country','Date', 'Region', 'Lat', 'Lon', 'tooltip_newcases', 'new_cases']])

def calculate_new_cases(df):
    unique_countries = df.Country.unique().tolist()

    output = [calc_newCases(df, c) for c in unique_countries]


    df_output = pd.concat(output)
    df_output.reset_index().to_feather("./parsed_data/new_confirmed.feather")

    return (df_output)

regional_confirmed = regional_summarize(all_countries, 'Confirmed', 'regional_confirmed.feather')
# regional_deaths = regional_summarize(all_countries, 'Deaths', 'regional_deaths.feather')
# regional_recovered = regional_summarize(all_countries, 'Recovered', 'regional_recovered.feather')

# Calculating a dataframe for the date, country and new confirmed cases that appeared that day.
calculate_new_cases(regional_confirmed)
