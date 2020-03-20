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
country_labs.columns = ['Countries', 'Region']

confirmed = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Confirmed.csv")
confirmed_long = ts_record_parse(confirmed, 'Confirmed')

pd.DataFrame(confirmed_long.Country.unique(), columns=["Countries"]).to_csv("country_list.csv", index=False, header=True)



deaths = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Deaths.csv")
deaths_long = ts_record_parse(deaths, "Deaths")


recovered = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_19-covid-Recovered.csv")
recovered_long = ts_record_parse(recovered, 'Recovered')


# Merging the timeseries data by day and location for COVID-19 confirmed cases, deaths, and recovered cases.
all_countries = confirmed_long.merge(deaths_long, on=["Province", "Country", "Lat", "Lon", "Date"]).merge(recovered_long, on=["Province", "Country", "Lat", "Lon", "Date"])

# Applying the region label (by continent) to the larger dataset
all_countries = pd.merge(all_countries, country_labs[["Countries", "Region"]], left_on="Country", right_on="Countries")
all_countries.to_feather("./parsed_data/all_countries_ts.feather")


# SUMMARIZING BY Date
# Summing all of the confirmed cases, deaths, and recovered patients for each day
data_totTime_confirmed = all_countries.groupby("Date")['Confirmed'].sum().reset_index()
data_totTime_deaths = all_countries.groupby("Date")['Deaths'].sum().reset_index()
data_totTime_recovered = all_countries.groupby("Date")['Recovered'].sum().reset_index()

all_countries_summary = copy.deepcopy(data_totTime_confirmed)
all_countries_summary = all_countries_summary.merge(data_totTime_deaths, on='Date').merge(data_totTime_recovered, on='Date')
all_countries_summary.head()

all_countries_summary.to_feather("./parsed_data/all_countries_summary.feather")


# Summarizing by country
def regional_summarize(df, var, file_name):

    fileout = './parsed_data/' + file_name
#     print(fileout)

    data_tsSum = df.groupby(['Country', 'Lat', 'Lon', 'Date', 'Region'])[var].sum()
    data_tsSum = data_tsSum.reset_index()
    
    data_tsSum_sort = data_tsSum.set_index("Country").sort_values(by='Date', ascending=True)
    data_tsSum_sort = data_tsSum_sort.reset_index()

    data_tsSum_sort.to_feather(fileout)

#     return(data_tsSum_sort)

#     return(data_tsSum_sort)
regional_summarize(all_countries, 'Confirmed', 'regional_confirmed.feather')
regional_summarize(all_countries, 'Deaths', 'regional_deaths.feather')
regional_summarize(all_countries, 'Recovered', 'regional_recovered.feather')
