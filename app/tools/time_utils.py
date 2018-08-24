import datetime, time


def str_2_datetime(str_in, input_format='%Y-%m-%d', timezone='JST'):
    return datetime.datetime.strptime(str_in, input_format)


def datetime_2_str(datetime_in, output_format='%Y-%m-%d'):
    return datetime_in.strftime(output_format)