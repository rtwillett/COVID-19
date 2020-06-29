import numpy as np
import pandas as pd
import copy

def ts_record_parse(df, var_title = "Value"):
    '''

    '''

    ts_cols = df.columns[4:] # Collect the names of all the columns named as a date
    ts_long = pd.melt(df, id_vars=['Province/State', 'Country/Region', 'Lat', 'Long'], value_vars=ts_cols, var_name='Date',
            value_name=var_title)
    ts_long['Date'] = pd.to_datetime(ts_long.Date)
    ts_long.columns = ["Province", "Country", "Lat", "Lon", "Date", var_title]
    return(ts_long)

def hongkong_isolate(df):
    '''
    Extracts the data for Hong Kong from the JHU data and creates a matching df format to the others used in this script
    '''

    hongkong_df = df.loc[df.Province == "Hong Kong"].copy()
    hongkong_df['Country'] = "Hong Kong"
    hongkong_df['Lat'] = 22.3193
    hongkong_df['Lon'] = 114.1694
    hongkong_df['Region'] = "Asia"

    hongkong_out = hongkong_df[['Country', 'Date', 'Region', 'Lat', 'Lon', 'Confirmed']].copy()
    hongkong_out['tooltip_confirmed'] = hongkong_out.apply(lambda x : x.Country + ": " + str(x.Confirmed), axis=1)

    return(hongkong_out)

def hongkong_extract(df_countryagg, df_raw):
    '''
    Gets the data for Hong Kong using he kongkong_isolate script, subtracts the HK numbers from China and updates the original dataframe with the new HK and China numbers.
    '''

    hk = hongkong_isolate(df_raw)
    hongkong_series = hk.Confirmed.to_numpy()

    china_slice = df_countryagg.loc[df_countryagg.Country == "China"].copy()
    china_confirmed = china_slice.Confirmed.to_numpy() # Extracting Confirmed column as a vector

    # Vectorized subtraction of the Hong Kong numbers from China numbers
    china_newConfirmed = np.subtract(china_confirmed, hongkong_series)

    # Extracting data from dataframe for all countries except China
    not_china = df_countryagg.loc[df_countryagg.Country != "China"]
    china_slice["Confirmed"] = china_newConfirmed.tolist()

    df_out = pd.concat([not_china, china_slice, hk])

    return(df_out)

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
#     data_tsSum_sort['tooltip_confirmed'] = data_tsSum_sort.apply(lambda x : x.Country + ": " + str(x.Confirmed), axis=1)
#     data_tsSum_sort['tooltip_deaths'] = df_out['tooltip_deaths'] = df_out.apply(lambda x : x.state + ": " + str(x.Deaths), axis=1)

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
country_labs.columns = ['Countries', 'Region', 'Lat', 'Lon', 'Subregion']

country_pop = pd.read_csv('./additional_data/WPP2019_TotalPopulationBySex.csv')
country_pop = country_pop[['Location', 'Time', 'PopTotal']].loc[country_pop.Time == 2020].drop_duplicates()
country_pop['PopTotal'] = country_pop.PopTotal.apply(lambda x: x * 1000)


confirmed_new = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv")
confirmed_long = ts_record_parse(confirmed_new, 'Confirmed')
confirmed_long["Country"] = confirmed_long.Country.apply(lambda x: x.replace("*", "")) # To remove the * from Taiwan

# Putting the tooltip label in for the mapdeck mouseover visualization in the Shiny app`
confirmed_long['tooltip_confirmed'] = confirmed_long.apply(lambda x : x.Country + ": " + str(x.Confirmed), axis=1)


deaths = pd.read_csv("./csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv")
deaths_long = ts_record_parse(deaths, "Deaths")
deaths_long["Country"] = deaths_long.Country.apply(lambda x: x.replace("*", "")) # To remove the * from Taiwan

# Putting the tooltip label in for the mapdeck mouseover visualization in the Shiny app`
deaths_long['tooltip_deaths'] = deaths_long.apply(lambda x : x.Country + ": " + str(x.Deaths), axis=1)


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

#Renaming the country names to align with the table it will be merged with
country_pop.replace({'China, Taiwan Province of China': 'Taiwan',
                     'United States of America': 'US',
                     'Iran (Islamic Republic of)': 'Iran',
                     'Viet Nam': 'Vietnam',
                     'Venezuala (Bolivarian Republic of)': 'Venezuala',
                     'Bolivia (Plurinational State of)': 'Bolia',
                     'Brunei Darussalem': 'Brunei',
                     'Republic of Moldova': 'Moldova',
                     'Russian Federation': 'Russia',
                     'Republic of Korea': 'Korea, South',
                     "Côte d'Ivoire": "Cote d'Ivoire",
                     'United Republic of Tanzania': 'Tanzania',
                     'Democratic Republic of the Congo': 'Congo (Kinshasa)',
                     'Republic of the Congo': 'Congo (Brazzaville)'}, inplace=True)

country_confirmed_newnorm = country_confirmed_new.merge(country_pop[["Location", 'PopTotal']], left_on="Country", right_on="Location").drop(columns=["Location"])
country_confirmed_newnorm["new_confirmed100k"] = country_confirmed_newnorm.apply(lambda x: normalize_measure(x.new_confirmed, x.PopTotal), axis=1)

country_deaths_newnorm = country_deaths_new.merge(country_pop[["Location", 'PopTotal']], left_on="Country", right_on="Location").drop(columns=["Location"])
country_deaths_newnorm["new_deaths100k"] = country_deaths_newnorm.apply(lambda x: normalize_measure(x.new_deaths, x.PopTotal), axis=1)

rolling_cases_country = [rolling_ave(country_confirmed_new, country, "new_confirmed") for country in countryList_newCases]
rolling_cases_country = pd.concat(rolling_cases_country)
rolling_cases_country = rolling_cases_country.merge(country_labs[["Countries", "Region"]], left_on='Country', right_on='Countries').drop(columns=["Countries"])

rolling_deaths_country = [rolling_ave(country_deaths_new, country, "new_deaths") for country in countryList_newCases]
rolling_deaths_country = pd.concat(rolling_deaths_country)
rolling_deaths_country = rolling_deaths_country.merge(country_labs[["Countries", "Region"]], left_on='Country', right_on='Countries').drop(columns=["Countries"])

# rolling_cases_country.reset_index(drop=True).to_feather('./parsed_data/rolling_cases_country.feather')
# rolling_deaths_country.reset_index(drop=True).to_feather('./parsed_data/rolling_deaths_country.feather')

rolling_cases_country.reset_index(drop=True).to_feather('./parsed_data/rolling_cases_country.feather')
rolling_deaths_country.reset_index(drop=True).to_feather('./parsed_data/rolling_deaths_country.feather')
