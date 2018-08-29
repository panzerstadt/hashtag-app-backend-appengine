import datetime, time


def str_2_datetime(str_in, input_format='%Y-%m-%d', timezone='JST'):
    return datetime.datetime.strptime(str_in, input_format)


def datetime_2_str(datetime_in, output_format='%Y-%m-%d'):
    return datetime_in.strftime(output_format)


def str_to_unix_timestamp(str_in=1535517446):
    if type(str_in) == str:
        str_in = int(str_in)

    # if you encounter a "year is out of range" error the timestamp
    # may be in milliseconds, try `ts /= 1000` in that case
    timestamp = datetime.datetime.utcfromtimestamp(str_in)
    dt = timestamp.strftime('%Y-%m-%d %H:%M:%S')

    #print("timestamp {} to datetime {}".format(timestamp, dt))

    return timestamp

