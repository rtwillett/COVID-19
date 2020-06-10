import numpy as np
import pandas as pd
import copy

def ts_record_parse(df, var_title = "Value"):
    '''
    Takes in the column version of data from the JHU dataset and makes it long form in tidy format.
    '''

    ts_cols = df.columns[4:] # Collect the names of all the columns named as a date
    ts_long = pd.melt(df, id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], value_vars=ts_cols, var_name='Date',
            value_name=var_title)
    ts_long['Date'] = pd.to_datetime(ts_long.Date)
    ts_long.columns = ["Province", "Country", "Lat", "Lon", "Date", var_title]
    return(ts_long)

# Summarizing by country
def regional_summarize(df, var, file_name):
    '''

    '''
#     var = var.lower()
    varname = "tooltip_" + var.lower()

    fileout = './parsed_data/' + file_name
#     print(fileout)

    data_tsSum = df.groupby(['Country', 'Date', 'Region', 'Lat', 'Lon'])[var].sum()
    data_tsSum = data_tsSum.reset_index()

    data_tsSum_sort = data_tsSum.set_index("Country").sort_values(by='Date', ascending=True)
    data_tsSum_sort = data_tsSum_sort.reset_index()

    data_tsSum_sort[varname] = data_tsSum_sort.apply(lambda x : x.Country + ": " + str(x[var]), axis=1)

    data_tsSum_sort.to_feather(fileout)

    return(data_tsSum_sort)

def calc_new(df, country, var):
    df_filt = df.loc[df.Country == country]

    varname = "new_" + var.lower()
    tooltip_name = "tooltip_new" + var.lower()

    if df_filt.shape[0] < 2:
        pass
    else:
        var_list = df_filt[var].to_list()

        new_var=[]
        for i in list(range(len(var_list)-1)):
            new_var.append(var_list[i+1] - var_list[i])
#             print(confirmed[i+1] - confirmed[i])

        df_out = df_filt.iloc[1:,:].copy()
        df_out[varname] = new_var
        df_out[tooltip_name] = df_out.apply(lambda x : x.Country + ": " + str(x[varname]), axis=1)

        return(df_out[['Country','Date', 'Region', 'Lat', 'Lon', tooltip_name, varname]])

def calculate_rate(df, var):
    unique_countries = df.Country.unique().tolist()

    varname = "new_" + var.lower()

    output = [calc_new(df, c, var) for c in unique_countries]


    df_output = pd.concat(output)
    df_output.reset_index().to_feather("./parsed_data/" + varname + ".feather")

    return (df_output)

country_labs = pd.read_csv('./additional_data/countries_labels.csv')
country_labs.columns = ['Countries', 'Region', 'Lat', 'Lon']

confirmed = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv")
confirmed_long = ts_record_parse(confirmed, 'Confirmed')
confirmed_long["Country"] = confirmed_long.Country.apply(lambda x: x.replace("*", "")) # To remove the * from Taiwan

# Putting the tooltip label in for the mapdeck mouseover visualization in the Shiny app`
confirmed_long['tooltip_confirmed'] = confirmed_long.apply(lambda x : x.Country + ": " + str(x.Confirmed), axis=1)


deaths = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv")
deaths_long = ts_record_parse(deaths, "Deaths")
deaths_long["Country"] = deaths_long.Country.apply(lambda x: x.replace("*", "")) # To remove the * from Taiwan

# Putting the tooltip label in for the mapdeck mouseover visualization in the Shiny app`
deaths_long['tooltip_deaths'] = deaths_long.apply(lambda x : x.Country + ": " + str(x.Deaths), axis=1)


# recovered = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_19-recovered_global.csv")
# recovered_long = ts_record_parse(recovered, 'Recovered')


# Merging the timeseries data by day and location for COVID-19 confirmed cases, deaths, and recovered cases.
all_countries = confirmed_long.merge(deaths_long, on=["Province", "Country", "Lat", "Lon", "Date"])#.merge(recovered_long, on=["Province", "Country", "Lat", "Lon", "Date"])

# With the group_by sums aggregating data across the countries, need to renew the geocode data. This will drop the old coordinates
all_countries.drop(columns=['Lat', 'Lon'], inplace=True)

# Applying the region label (by continent) to the larger dataset
all_countries = pd.merge(all_countries, country_labs, left_on="Country", right_on="Countries")
all_countries.to_feather("./parsed_data/all_countries_ts.feather")


# SUMMARIZING BY Date
# Summing all of the confirmed cases, deaths, and recovered patients for each day
data_totTime_confirmed = all_countries.groupby("Date")['Confirmed'].sum().reset_index()


data_totTime_deaths = all_countries.groupby("Date")['Deaths'].sum().reset_index()


# data_totTime_recovered = all_countries.groupby("Date")['Recovered'].sum().reset_index()

all_countries_summary = copy.deepcopy(data_totTime_confirmed)
all_countries_summary = all_countries_summary.merge(data_totTime_deaths, on='Date')#.merge(data_totTime_recovered, on='Date')

all_countries_summary.to_feather("./parsed_data/all_countries_summary.feather")



regional_confirmed = regional_summarize(all_countries, 'Confirmed', 'regional_confirmed.feather')
regional_deaths = regional_summarize(all_countries, 'Deaths', 'regional_deaths.feather')
# regional_recovered = regional_summarize(all_countries, 'Recovered', 'regional_recovered.feather')

# Calculating a dataframe for the date, country and new confirmed cases that appeared that day.
country_confirmed_new = calculate_rate(regional_confirmed, "Confirmed")
country_deaths_new = calculate_rate(regional_deaths, "Deaths")

def rolling_ave_calc(df, var):
    testing = df.set_index('Date')[[var]] #loc[df.abbrev == "TX"][["date", "state", var]]
    testing_roll = testing.rolling(window=7, min_periods=1).mean().reset_index()
    return testing_roll

def rolling_ave(df, country, var):
    df_sub = df.loc[df.Country == country][["Date", "Country", var]]
    df_rolling = rolling_ave_calc(df_sub, var)
    df_rolling["Country"] = country
    return df_rolling

countryList_newCases = country_confirmed_new.Country.unique().tolist()

def normalize_measure(num1, num2):
    norm_val = num1/num2*100000
    return norm_val

country_confirmed_newnorm = country_confirmed_new.merge(country_pop[["name", 'pop2020']], left_on="Country", right_on="name").drop(columns=["name"])
country_confirmed_newnorm["new_confirmed100k"] = country_confirmed_newnorm.apply(lambda x: normalize_measure(x.new_confirmed, x.pop2020), axis=1)

rolling_cases_country = [rolling_ave(country_confirmed_new, country, "new_confirmed") for country in countryList_newCases]
rolling_cases_country = pd.concat(rolling_cases_country)
rolling_cases_country = rolling_cases_country.merge(country_labs[["Countries", "Region"]], left_on='Country', right_on='Countries').drop(columns=["Countries"])

rolling_deaths_country = [rolling_ave(country_deaths_new, country, "new_deaths") for country in countryList_newCases]
rolling_deaths_country = pd.concat(rolling_deaths_country)
rolling_deaths_country = rolling_deaths_country.merge(country_labs[["Countries", "Region"]], left_on='Country', right_on='Countries').drop(columns=["Countries"])

rolling_cases_country.reset_index(drop=True).to_feather('./parsed_data/rolling_cases_country.feather')
rolling_deaths_country.reset_index(drop=True).to_feather('./parsed_data/rolling_deaths_country.feather')
