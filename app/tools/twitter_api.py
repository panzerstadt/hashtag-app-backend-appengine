import json
import yweather
import datetime
import pytz

import twitter
from hidden.hidden import Twitter

from tools.db_utils import load_db, update_db
from tools.time_utils import str_2_datetime, datetime_2_str
from tools.baseutils import get_filepath

db_path = get_filepath('./db/daily_database.json')
time_format_full_with_timezone = '%Y-%m-%d %H:%M:%S%z'
time_format_full_no_timezone = '%Y-%m-%d %H:%M:%S'
time_format_twitter_trends = '%Y-%m-%dT%H:%M:%SZ'
jp_timezone = pytz.timezone('Asia/Tokyo')

t_secrets = Twitter()
consumer_key = t_secrets.consumer_key
consumer_secret = t_secrets.consumer_secret
access_token_key = t_secrets.access_token_key
access_token_secret = t_secrets.access_token_secret

api = twitter.Api(consumer_key=consumer_key,
                  consumer_secret=consumer_secret,
                  access_token_key=access_token_key,
                  access_token_secret=access_token_secret,
                  sleep_on_rate_limit=True)


# API call
def get_top_trends_from_twitter_api(country='Japan', exclude_hashtags=True):
    """
    what is it useful for?
    participation. from twitter API docs

    How can I participate in a trend?
    Simply post a Tweet including the exact word or phrase as it appears in the trends list
    (with the hashtag, if you see one). Due to the large number of people Tweeting about these
    specific trends, you may not always be able to find your particular Tweet in search, but
    your followers will always see your Tweets.

    twitter Ads API has a keyword insights endpoint
    ref: https://developer.twitter.com/en/docs/ads/audiences/api-reference/keyword-insights.html#
    :param filter:
    :return:
    """
    # this stupid WOEID requires yweather to get (a library), because YAHOO itself has stopped supporting it
    # WOEID
    woeid_client = yweather.Client()
    woeid = woeid_client.fetch_woeid(location=country)

    if exclude_hashtags :
        trends = api.GetTrendsWoeid(woeid, exclude='hashtags')
    else:
        trends = api.GetTrendsWoeid(woeid, exclude=None)

    output = []
    for trend in trends:
        trend = trend.AsDict()

        # get volumes
        try:
            tw_volume = int(trend['tweet_volume']),
        except:
            tw_volume = [0]

        # match time with timezone
        timestamp_str = trend['timestamp']  # this is utc
        timestamp_dt = str_2_datetime(timestamp_str, input_format=time_format_twitter_trends).replace(tzinfo=pytz.utc)

        # timestamp_local = timestamp_dt.astimezone(tz=pytz.utc)
        timestamp_utc_str = datetime_2_str(timestamp_dt, output_format=time_format_full_with_timezone)

        output.append({
            "label": trend['name'],
            "volume": tw_volume,
            "time": timestamp_utc_str,
            "query": trend['query'],
            "url": trend['url']
        })

    output_json = json.dumps(output, ensure_ascii=False)
    return output_json


# database call and caching
def get_top_trends_from_twitter(country='Japan', exclude_hashtags=False, debug=False, cache_duration_mins=15, append_db=True):
    cache_db = load_db(database_path=db_path, debug=False)
    trends_db = cache_db['trends']
    if exclude_hashtags:
        trends_cache = trends_db['exclude_hashtags']
    else:
        trends_cache = trends_db['include_hashtags']

    # compare db and now
    try:
        db_timestamp = str_2_datetime(trends_cache['timestamp'], input_format=time_format_full_with_timezone)
    except ValueError:
        db_timestamp = str_2_datetime(trends_cache['timestamp'], input_format=time_format_full_no_timezone)
        db_timestamp = db_timestamp.astimezone(tz=pytz.utc)

    rq_timestamp = datetime.datetime.now(tz=pytz.utc)

    time_diff = rq_timestamp - db_timestamp
    print('time since last trends API call: {} (h:m:s)'.format(time_diff))
    print('time diff in seconds: {}'.format(time_diff.seconds))
    print('time in db: {}'.format(db_timestamp))
    print('time in rq: {}'.format(rq_timestamp))
    if time_diff.seconds < cache_duration_mins*60:
        print('less than cache duration, returning cache')
        output_json = json.dumps(trends_cache['content'], ensure_ascii=False)
        return output_json
    else:
        output_json = get_top_trends_from_twitter_api(country=country, exclude_hashtags=exclude_hashtags)
        # update
        output_list = json.loads(output_json)

        if append_db:
            output_list = trends_cache['content'] + output_list
            
        if exclude_hashtags:
            cache_db['trends']['exclude_hashtags']['content'] = output_list
            cache_db['trends']['exclude_hashtags']['timestamp'] = datetime_2_str(rq_timestamp, output_format=time_format_full_with_timezone)
        else:
            cache_db['trends']['include_hashtags']['content'] = output_list
            cache_db['trends']['include_hashtags']['timestamp'] = datetime_2_str(rq_timestamp, output_format=time_format_full_with_timezone)

        update_db(cache_db, database_path=db_path, debug=debug)
        return output_json


# API call
def get_top_hashtags_from_twitter_api(country='Japan', debug=False):
    """
    an extension of get_top_trends_from_twitter()
    make an API call for top trends, then visit each URL to get grab hashtags from top 10 twitter posts
    :return:
    """
    trends = get_top_trends_from_twitter(country=country, exclude_hashtags=False)
    trends = json.loads(trends)

    trending_hashtags = [t['label'] for t in trends]

    #print(json.dumps(trends, indent=4, ensure_ascii=False))

    queries = [t['query'] for t in trends]

    if debug:
        #[print(x) for x in trends]
        #[print(x) for x in queries]
        queries = [queries[0]]

    full_hashtags_list = []
    for query in queries:
        #print(query)
        # there is no country filter, but there is language filter at least
        if country == 'Japan':
            responses = api.GetSearch(term=query, locale='ja', return_json=True)
            try: responses = responses['statuses']
            except: print(responses)
        else:
            responses = api.GetSearch(term=query, return_json=True)
            try: responses = responses['statuses']
            except: print(responses)

        #print(json.dumps(responses, indent=4, ensure_ascii=False))

        trend_hashtags_list = []
        for response in responses:
            if debug: print(json.dumps(response, indent=4, ensure_ascii=False))
            text = response['text']

            hashtags_list = response['entities']['hashtags']

            if len(hashtags_list) > 0:
                hashtags_list = [h['text'] for h in hashtags_list]
                [trend_hashtags_list.append(h) for h in hashtags_list]

        full_hashtags_list.append(trend_hashtags_list)

    flat_hashtags_list = [item for sublist in full_hashtags_list for item in sublist]

    # turn it into a set to clear duplicates, then append #
    flat_hashtags_list = list(set(flat_hashtags_list))
    flat_hashtags_list = ['#'+h for h in flat_hashtags_list]

    flat_tier_list = []
    for h in flat_hashtags_list:
        if h in trending_hashtags:
            flat_tier_list.append(1)
        else:
            flat_tier_list.append(2)

    output = []
    for hashtag, tier in zip(flat_hashtags_list, flat_tier_list):
        output.append({
            "label": hashtag,
            "tier": tier
        })

    sorted_output = sorted(output, key=lambda x: x['tier'])

    output_json = json.dumps(sorted_output, ensure_ascii=False)
    return output_json


# database call and caching
def get_top_hashtags_from_twitter(country='Japan', debug=False, cache_duration_mins=15, append_db=True):
    cache_db = load_db(database_path=db_path, debug=False)
    hashtags_cache = cache_db['hashtags']

    # compare db and now
    db_timestamp = str_2_datetime(hashtags_cache['timestamp'], input_format=time_format_full_with_timezone)
    db_timestamp = db_timestamp.astimezone(tz=pytz.utc)

    rq_timestamp = datetime.datetime.now(tz=pytz.utc)

    time_diff = rq_timestamp - db_timestamp
    print('time since last hashtags API call: {}'.format(time_diff))
    if time_diff.seconds < cache_duration_mins * 60:
        # DB
        output_json = json.dumps(hashtags_cache['content'], ensure_ascii=False)
        return output_json
    else:
        output_json = get_top_hashtags_from_twitter_api(country=country, debug=debug)
        # update
        output_list = json.loads(output_json)

        if append_db:
            output_list = hashtags_cache['content'] + output_list

        cache_db['hashtags']['content'] = output_list
        cache_db['hashtags']['timestamp'] = datetime_2_str(rq_timestamp, output_format=time_format_full_with_timezone)

        update_db(cache_db, database_path=db_path, debug=debug)
        return output_json


if __name__ == '__main__':
    country = 'Japan'
    t = json.loads(get_top_hashtags_from_twitter_api(country=country))

    [print(x) for x in t]
    print(len(t))