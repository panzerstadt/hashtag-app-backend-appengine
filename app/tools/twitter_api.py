import json
import yweather
import datetime
import pytz
from urllib import parse

import twitter

try:
    from hidden.hidden import Twitter

    from tools.db_utils import load_db, update_db
    from tools.time_utils import str_2_datetime, datetime_2_str, str_to_unix_timestamp
    from tools.baseutils import get_filepath
except:
    from app.hidden.hidden import Twitter

    from app.tools.db_utils import load_db, update_db
    from app.tools.time_utils import str_2_datetime, datetime_2_str, str_to_unix_timestamp
    from app.tools.baseutils import get_filepath


db_path = get_filepath('./db/daily_database.json')
trends_db_path = get_filepath('./db/daily_trend_search_database.json')
top_retweets_db_path = get_filepath('./db/daily_top_rt_database.json')

time_format_full_with_timezone = '%Y-%m-%d %H:%M:%S%z'
time_format_full_no_timezone = '%Y-%m-%d %H:%M:%S'
time_format_twitter_trends = '%Y-%m-%dT%H:%M:%SZ'
time_format_twitter_created_at = '%a %b %d %H:%M:%S %z %Y'

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


def check_rate_limit(endpoint="GetSearch", debug=False):
    # check time now
    time_now = datetime.datetime.utcnow()

    if debug:
        print("time now: ", time_now)
        print("timestamp now: ", time_now.timestamp())

    # twitter get rate limits from endpoint
    api.InitializeRateLimit()

    response = api.rate_limit
    rl = response.resources

    if endpoint.lower() == "getsearch":
        output = rl['search']
        # 180 searches per 15 mins
    elif endpoint.lower() == "trends":
        output = rl['trends']
    else:
        output = rl['search']

    if debug:
        print(json.dumps(rl, indent=4, ensure_ascii=False))

    rl_output = []
    rl_output.append('')
    rl_output.append('rate limit for {}:'.format(endpoint))
    rl_output.append(str(output))
    rl_output.append('')

    # diff
    for k, v in output.items():
        diff = str_to_unix_timestamp(v['reset']) - time_now
        diff_mins = diff.total_seconds() / 60
        rl_output.append('endpoint "{}" refreshes in {:.2f} minutes'.format(k, diff_mins))

    rl_output.append('')

    rl_output = '\n'.join(rl_output)
    return rl_output


# API call
def get_search_tweets(query="pokemon", return_list=['media', 'text', 'hashtags', 'favorite_count', 'retweet_count', 'retweeted_status', 'id'], count=100, debug=False):
    """
    search limit: 180 / 15 mins
    status limit:
    :param query:
    :return:
    """
    # currently limited to japanese, as a way to geofence searches to Japan
    response = api.GetSearch(lang="ja", term=query, count=count)

    output = []
    for r in response:
        r = r.AsDict()

        if debug:
            print('')
            print("response")
            print(json.dumps(r, indent=4, ensure_ascii=False))

        # keys are the things you want from the definition
        return_dict = {}
        if return_list:
            for k in return_list:
                try:
                    return_dict[k] = r[k]
                except KeyError:
                    return_dict[k] = {}

        output.append(return_dict)

    return output


# currently set to only look at japan's top performing tweets with images
def get_search_tweet_images_raw(raw_query="q=min_retweets%3A10000%20filter%3Aimages%20lang%3Aja", return_list=['media', 'text', 'hashtags', 'retweet_count', 'favorite_count', 'retweeted_status', 'id', 'created_at'], debug=False):
    """
    buzz machine recommendation
    :param raw_query:
    :return:
    """
    def escape_raw_query(raw_query):
        out = parse.quote(raw_query, safe="=")
        return out

    raw_query = escape_raw_query(raw_query)

    # currently limited to japanese, as a way to geofence searches to Japan
    response = api.GetSearch(raw_query=raw_query)

    output = []
    for r in response:
        r = r.AsDict()

        if debug:
            print('')
            print("response")
            print(json.dumps(r, indent=4, ensure_ascii=False))

        # keys are the things you want from the definition
        return_dict = {}
        if return_list:
            for k in return_list:
                try:
                    return_dict[k] = r[k]
                except KeyError:
                    return_dict[k] = {}

        output.append(return_dict)

    return output


def process_tweets(tweets_response, keep_all=False, debug=False):
    """
    by default, processing discards tweets with no retweets or likes
    keep_all=False keeps all tweets, whether they have retweets or not

    :param tweets_response:
    :param keep_all:
    :param debug:
    :return:
    """
    tweets = tweets_response

    #print(json.dumps(tweets, indent=4, ensure_ascii=False))

    output_tweets = []
    for tweet in tweets:
        # loop through every tweet
        output_tweet = {}
        output_tweet['likes'] = 0
        for k, v in tweet.items():
            if k == "favorite_count" or k == "retweeted_status":
                # print('checking favorite_count at {}'.format(k))
                # print(v)
                if k == "favorite_count" and v:
                    output_tweet['likes'] = v
                elif k == "retweeted_status" and v:
                    # print("rt:", v)
                    try:
                        output_tweet['likes'] = v['favorite_count']
                    except:
                        print('favorites not found')
                        print(v)
                        pass

            elif k == "media" and v:
                # turn media dict into img url
                output_tweet[k] = []
                for m in v:
                    output_tweet[k].append(m['media_url_https'])

            elif k == "id" and v:
                # make url from id and dispose id
                output_tweet['url'] = "https://twitter.com/anyuser/status/" + str(v)

            elif k == "retweet_count":
                if v:
                    if debug: print('       picking this: ', k, v)
                    output_tweet[k] = v
                else:
                    if debug: print('       skipping this: ', k, v)
                    # not keeping those with 0 RT
                    output_tweet[k] = 0

            elif k == "created_at":
                tweet_creation_time = str_2_datetime(v, input_format=time_format_twitter_created_at)
                tweet_checked_time = datetime.datetime.now(tz=pytz.utc)

                output_tweet['timestamp'] = {
                    "created": datetime_2_str(tweet_creation_time, output_format=time_format_full_with_timezone),
                    "last_checked": datetime_2_str(tweet_checked_time, output_format=time_format_full_with_timezone)
                }

            else:
                # keep k:v same
                if debug: print('keeping this: ', k, repr(v))
                output_tweet[k] = v

        print('num of likes: ', output_tweet['likes'])

        output_tweets.append(output_tweet)

    output = []
    if not keep_all:
        for o in output_tweets:
            if o['likes'] > 0 and o['retweet_count'] > 0:
                output.append(o)
    else:
        output = output_tweets

    return output


# helper function for search_tweets
def analyze_trending_keyword(keyword="pokemon", count=100, keep_all=False, debug=False):
    """
    i can do a 180 of these every 15 mins
    meaning i can analyze 180 keywords every 15 mins, returning all images
    :param keyword:
    :return:
    """
    print('analyzing keyword: {}'.format(keyword))
    tweets = get_search_tweets(query=keyword, count=count, debug=debug)

    return process_tweets(tweets, keep_all=keep_all, debug=debug)


def analyze_top_retweets(min_retweets=10000, debug=False):
    query = "q=min_retweets:{}".format(min_retweets)
    query += " filter:images lang:ja"

    tweets = get_search_tweet_images_raw(raw_query=query)
    return process_tweets(tweets, keep_all=True, debug=debug)


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

    check_rate_limit()

    if exclude_hashtags :
        trends = api.GetTrendsWoeid(woeid, exclude='hashtags')
    else:
        trends = api.GetTrendsWoeid(woeid, exclude=None)

    output = []
    images_output = []
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
            "url": trend['url'],
        })

        images_output.append({
            "label": trend['name'],
            "time": timestamp_utc_str,
            "tweets": analyze_trending_keyword(trend['name'], count=50)
        })

    output_json = json.dumps(output, ensure_ascii=False)
    images_output_json = json.dumps(images_output, ensure_ascii=False)
    return output_json, images_output_json


# API call (for extended search)
def get_top_hashtags_from_twitter_api(country='Japan', extended_search=True, debug=False):
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


# naive twitter api call
def get_update_top_posts_from_twitter(min_retweets=10000, cache_duration_mins=15, debug=False, append_db=True):
    """
        also updates daily trends db, but doesn't return it
        :param country:
        :param exclude_hashtags:
        :param debug:
        :param cache_duration_mins:
        :param append_db:
        :return:
        """
    # load retweets db
    top_retweets_db = load_db(database_path=top_retweets_db_path, debug=False)
    top_posts_cache = top_retweets_db['top_posts']


    output_list = analyze_top_retweets(min_retweets=min_retweets, debug=debug)

    if append_db:
        # check for same post
        for o in output_list:
            # apparently [:] changes list in place (saves ram)
            # cuts away duplicates of tweets
            top_posts_cache[:] = [d for d in top_posts_cache if d.get('url') != o['url']]

        # adds new tweets at the end
        output_list = top_posts_cache + output_list

    top_retweets_db['top_posts'] = output_list

    update_db(top_retweets_db, database_path=top_retweets_db_path, debug=debug)

    print('top posts db updated.')

    del top_retweets_db
    del top_posts_cache
    del output_list

    print('memory freed.')


# database call and caching
def get_top_trends_from_twitter(country='Japan', exclude_hashtags=False, debug=False, cache_duration_mins=15, append_db=True):
    """
    also updates daily trends db, but doesn't return it
    for trends, timestamp used is in time called

    :param country:
    :param exclude_hashtags:
    :param debug:
    :param cache_duration_mins:
    :param append_db:
    :return:
    """
    # load main db
    cache_db = load_db(database_path=db_path, debug=False)
    trends_db = cache_db['trends']

    if exclude_hashtags:
        trends_cache = trends_db['exclude_hashtags']
    else:
        trends_cache = trends_db['include_hashtags']

    # load trends + top retweets db
    trend_search_db = load_db(database_path=trends_db_path, debug=False)



    # MAIN_DB ONLY
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
        output_json, img_output_json = get_top_trends_from_twitter_api(country=country, exclude_hashtags=exclude_hashtags)
        # update
        output_list = json.loads(output_json)
        trend_search_list = json.loads(img_output_json)

        if append_db:
            output_list = trends_cache['content'] + output_list
            trend_search_list = trend_search_db['trends'] + trend_search_list
            
        if exclude_hashtags:
            cache_db['trends']['exclude_hashtags']['content'] = output_list
            cache_db['trends']['exclude_hashtags']['timestamp'] = datetime_2_str(rq_timestamp, output_format=time_format_full_with_timezone)
        else:
            cache_db['trends']['include_hashtags']['content'] = output_list
            cache_db['trends']['include_hashtags']['timestamp'] = datetime_2_str(rq_timestamp, output_format=time_format_full_with_timezone)

        trend_search_db['trends'] = trend_search_list

        update_db(cache_db, database_path=db_path, debug=debug)
        update_db(trend_search_db, database_path=trends_db_path, debug=debug)

        print('trends and image database updated.')

        del cache_db
        del trends_db
        del trends_cache
        del trend_search_db
        del trend_search_list
        del output_list
        del output_json
        del img_output_json

        print('memory freed.')


def check_db(db_path=top_retweets_db_path):
    db = load_db(db_path)

    c = db['top_posts']

    [print(repr(x['text'])) for x in c]
    print('number of posts: ', len(c))
    del db
    del c


if __name__ == '__main__':
    country = 'Japan'
    # t = json.loads(get_top_hashtags_from_twitter_api(country=country))
    #
    # [print(x) for x in t]
    # print(len(t))

    #t = get_search_tweets(query='AIG', count=5, debug=False)
    #t = get_search_tweet_images_raw(raw_query="q=min_retweets:10000 filter:images lang:ja", debug=True)
    #
    # [print(json.dumps(x, indent=4, ensure_ascii=False)) for x in t]

    w = analyze_trending_keyword(keyword='雲の流れ', count=100, debug=False)
    # w = analyze_top_retweets(debug=True)
    #
    print('\n\n\n\noutput')
    print(w)
    #
    #[print(json.dumps(x, indent=4, ensure_ascii=False)) for x in w]

    # get_update_top_posts_from_twitter(append_db=True)
    # check_db()

    t = check_rate_limit()
    print(t)