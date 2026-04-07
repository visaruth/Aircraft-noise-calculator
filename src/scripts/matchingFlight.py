import pandas as pd
import datetime as datetime


def find_flight_peak(flights, peaks):
    min_peak, max_peak = min(peaks["start_time"]), max(peaks["end_time"])
    flights_peaks = flights[
        (flights["datetime"] > min_peak) & (flights["datetime"] < max_peak)
    ]
    return flights_peaks


def match_cond(start, stop, date_time, lag_width):
    return (date_time >= start - datetime.timedelta(milliseconds=lag_width * 1000)) & (
        date_time <= stop + datetime.timedelta(milliseconds=lag_width * 1000)
    )


def match_peak(flights, peaks, lag_width):
    # matched = [flights[match_cond(start,stop,flights['datetime'],lag_width)] for start, stop in zip(peaks['start_time'], peaks['end_time']) if len(flights[match_cond(start,stop,flights['datetime'],lag_width)]) > 0]
    matched = []
    for start, stop, leq in zip(peaks["start_time"], peaks["end_time"], peaks["Leq"]):
        df = flights[match_cond(start, stop, flights["datetime"], lag_width)]
        if len(df) > 0:
            df = df.assign(Leq=leq)
            matched.append(df)

    print(len(matched) / len(peaks))

    df_matched = pd.concat(matched).reset_index(drop=True)
    return df_matched
