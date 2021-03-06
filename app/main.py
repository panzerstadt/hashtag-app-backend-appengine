#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

from tools.baseutils import textify
import time, datetime, pytz
import schedule
from threading import Thread

from tools.twitter_api import get_top_trends_from_twitter, get_top_hashtags_from_twitter, get_update_top_posts_from_twitter, check_rate_limit
from tools.db_utils import make_db, load_db, update_db, adjust_images_db, adjust_top_posts_db
from tools.time_utils import datetime_2_str, str_2_datetime

# pretty interface
from flasgger import Swagger

allowed_domains = [
    r'*',
]

app = Flask(__name__)
swagger = Swagger(app)
app.config.update(JSON_AS_ASCII=False,
                  JSONIFY_PRETTYPRINT_REGULAR=True)
CORS(app,
     origins=allowed_domains,
     resources=r'*',
     supports_credentials=True)


start_time = time.time()
update_start = time.time()
time_format_full_no_timezone = '%Y-%m-%d %H:%M:%S'
time_format_full_with_timezone = '%Y-%m-%d %H:%M:%S%z'
jp_timezone = pytz.timezone('Asia/Tokyo')

DATABASE_PATH = './db/daily_database.json'
TRENDS_DATABASE_PATH = './db/daily_trend_search_database.json'
TOP_RETWEETS_DATABASE_PATH = './db/daily_top_rt_database.json'
DATABASE_STRUCTURE = {
    "trends": {
        "include_hashtags": {
            "timestamp": '1999-01-01 00:00:00+0000',
            "initial_timestamp": datetime_2_str(datetime.datetime.now(tz=pytz.utc), output_format=time_format_full_with_timezone),
            "content": []
        },
        "exclude_hashtags": {
            "timestamp": '1999-01-01 00:00:00+0000',
            "initial_timestamp": datetime_2_str(datetime.datetime.now(tz=pytz.utc), output_format=time_format_full_with_timezone),
            "content": []
        }
    },
    "hashtags": {
        "timestamp": '1999-01-01 00:00:00+0000',
        "initial_timestamp": datetime_2_str(datetime.datetime.now(tz=pytz.utc), output_format=time_format_full_with_timezone),
        "content": []
    }
}

REFRESH_MINS = 15


def run_schedule():
    while 1:
        schedule.run_pending()
        time.sleep(1)


def get_twitter_trends():
    print("Elapsed time: " + str(time.time() - start_time))
    print('calling twitter API to get trends')

    get_top_trends_from_twitter(country='Japan', cache_duration_mins=REFRESH_MINS-1)


def get_twitter_extended_hashtags():
    print("Elapsed time: " + str(time.time() - start_time))
    print('calling twitter API to build hashtags')

    get_top_hashtags_from_twitter(country='Japan', cache_duration_mins=REFRESH_MINS-1)


def get_updates_from_twitter():
    update_start = time.time()

    get_twitter_trends()
    adjust_images_db()
    get_update_top_posts_from_twitter()
    adjust_top_posts_db()
    #get_twitter_extended_hashtags()

    print("total update time took: {} seconds".format(str(time.time() - update_start)))


# only POST
@app.route('/', methods=['GET'])
def daily():
    print("time since app start: {:.2f} minutes".format((time.time() - start_time) / 60))
    print("time since last update: {:.2f} minutes".format((time.time() - update_start) / 60))

    output = {
        "endpoints": {
            "/": "landing page",
            "/twitter/hashtags": "currently not supported",
            "/twitter/trends": "returns minimal trends db since the beginning of time",
            "/twitter/trends/images": "returns minimal images db since the beginning of time",
            "/twitter/top_posts": "returns top N tweets since the beginning of time (default 30)",
            "/twitter/rate_limit": "checks twitter for rate limiting",
            "/db": "full database, VERY HEAVY",
        }
    }

    return jsonify(output)


@app.route('/twitter/hashtags')
def hashtags_twitter_only():
    """
        get list of latest tweets, locations, sentiment, and time
        ---
        parameters:
          - name: location
            in: query
            type: string
            required: true
            default: osaka
        responses:
          200:
            description: returns a json list of tweets
            schema:
              id: predictionGet
              properties:
                results:
                  type: json
                  default: setosa
                status:
                  type: number
                  default: 200
    """
    print("time since app start: {:.2f} minutes".format(str((time.time() - start_time) / 60)))
    print("time since last update: {:.2f} minutes".format(str((time.time() - update_start) / 60)))

    full_db = load_db(database_path=DATABASE_PATH)

    direct_hashtags_from_trends = full_db['trends']['include_hashtags']['content']

    output = []
    for t in direct_hashtags_from_trends:
        output.append(t['label'])

    output_str = '<br />'.join(output)
    return textify(output_str)


@app.route('/db', methods=['GET'])
def all():
    """
        the full database. use to get updated db before updating container
        ---
        responses:
          200:
            description: returns database
            schema:
              id: databaseGet
              properties:
                results:
                  type: json
                  default: {trends: {include_hashtags: {}, exclude_hashtags: {}, hashtags: {}}
                status:
                  type: number
                  default: 200
    """
    args = request.args.get('q')
    if not args:
        args = "main"

    if args == "main":
        full_db = load_db(database_path=DATABASE_PATH)

        db_init_timestamp = str_2_datetime(full_db['trends']['include_hashtags']['initial_timestamp'], input_format=time_format_full_with_timezone)
        db_update_timestamp = str_2_datetime(full_db['trends']['include_hashtags']['timestamp'], input_format=time_format_full_with_timezone)

        print("time since app start: {:.2f} minutes".format((time.time() - start_time) / 60))
        print("time since database init: {:.2f} hours".format((datetime.datetime.now(tz=pytz.utc) - db_init_timestamp).seconds/3600))
        print("time since last update: {:.2f} minutes".format((datetime.datetime.now(tz=pytz.utc) - db_update_timestamp).seconds/60))

    elif args == "trends":
        full_db = load_db(database_path=TRENDS_DATABASE_PATH)
    elif args == "top_posts":
        full_db = load_db(database_path=TOP_RETWEETS_DATABASE_PATH)

    return jsonify(full_db)


@app.route('/db/backup', methods=['GET'])
def backup():
    backup_db = load_db(database_path=DATABASE_PATH + '.bak')
    return jsonify(backup_db)


@app.route('/twitter/trends', methods={'GET'})
def trends():
    """
        loads trends database
        ---
        responses:
          200:
            description: returns database
            schema:
              id: databaseGet
              properties:
                results:
                  type: json
                  default: {content: {}, timestamp: "", initial_timestamp: ""}
                status:
                  type: string
                  default: ok
    """
    full_db = load_db(database_path=DATABASE_PATH)

    db_init_timestamp = str_2_datetime(full_db['trends']['include_hashtags']['initial_timestamp'],
                                       input_format=time_format_full_with_timezone)

    db_update_timestamp = str_2_datetime(full_db['trends']['include_hashtags']['timestamp'],
                                         input_format=time_format_full_with_timezone)


    print("time since app start: {:.2f} minutes".format((time.time() - start_time) / 60))
    print("time since database init: {}".format(
        (datetime.datetime.now(tz=pytz.utc) - db_init_timestamp)))
    print("time since last update: {:.2f} minutes".format(
        (datetime.datetime.now(tz=pytz.utc) - db_update_timestamp).seconds / 60))
    print('\ndebug:')
    print('time now: {}'.format(datetime.datetime.now(tz=pytz.utc)))
    print('db init time: {}'.format(db_init_timestamp))
    print('diff: {}'.format(datetime.datetime.now(tz=pytz.utc) - db_init_timestamp))

    # send back only a portion of the db
    results = full_db['trends']['include_hashtags']
    del full_db

    contents = results['content']

    output_content = []
    for c in contents:
        output_content.append({
            "label": c['label'],
            "time": c['time'],
            "volume": c['volume']
        })

    output_results = {
        "content": output_content,
        "timestamp": results['timestamp'],
        "initial_timestamp": results['initial_timestamp']
    }

    trends_output = {
        "results": output_results,
        "status": 'ok'
    }

    return jsonify(trends_output)


@app.route('/twitter/trends/images', methods=['GET'])
def images():
    full_db = load_db(database_path=TRENDS_DATABASE_PATH)

    # from trends content
    # send back only a portion of the db
    contents = full_db['trends']
    del full_db

    output_content = []
    for c in contents:
        output_media_url = []
        try:
            for t in c['tweets']:
                if t['media']:
                    output_media_url.append({
                        "url": t['url'],
                        "images": t['media']
                    })
        except:
            continue

        output_content.append({
            "label": c['label'],
            "time": c['time'],
            "media": output_media_url
        })

    output_results = {
        "content": output_content
    }

    trends_output = {
        "results": output_results,
        "status": 'ok'
    }

    return jsonify(trends_output)


@app.route('/twitter/top_posts', methods=['GET'])
def top_posts():
    try:
        arg = int(request.args.get('count'))
        if not arg:
            arg = 100
    except:
        arg = 100

    full_db = load_db(database_path=TOP_RETWEETS_DATABASE_PATH)

    # from trends content
    # send back only a portion of the db
    contents = full_db['top_posts']
    del full_db

    print('returning {} most recent items from db'.format(arg))

    output = {
        "results": contents[arg*-1:],
        "status": "ok"
    }

    return jsonify(output)


@app.route('/twitter/rate_limit', methods={'GET'})
def ratelimit():
    """
    return rate limit
    :return:
    """
    rl_search = check_rate_limit(endpoint='GetSearch')
    rl_trends = check_rate_limit(endpoint='trends')

    rl = '\n'.join([rl_search, rl_trends]).replace('\n', '<br/>')

    return render_template_string(rl)



if __name__ == '__main__':
    make_db(DATABASE_STRUCTURE, debug=True)
    get_updates_from_twitter()

    # right now i am using flask dev server because of the timing loop
    # but if i am confident in my caching system i can probably use the production server and
    schedule.every(REFRESH_MINS).minutes.do(get_updates_from_twitter)
    t = Thread(target=run_schedule)
    t.start()
    print("Start time: " + str(start_time))
    app.run(debug=True, host='0.0.0.0', port=8080, use_reloader=False)
    print('a flask app is initiated at {0}'.format(app.instance_path))


