import json
import os


db_path = './db/daily_database.json'
img_db_path = './db/daily_trend_search_database.json'
top_retweets_db_path = './db/daily_top_rt_database.json'


def load_db(database_path=db_path, debug=False):
    with open(database_path, 'r') as json_db:
        return json.load(json_db)


def update_db(dict_in, database_path=db_path, debug=False):
    with open(database_path, 'r') as json_db:
        state_str = json_db.read()
        state = json.loads(state_str)
        if debug:
            print('current state')
            print(json.dumps(state, indent=4, ensure_ascii=False))
            print('replacing state (this is not redux yet)')

        # update logic
        for k, v in dict_in.items():
            state[k] = dict_in[k]

    with open(database_path + '.tmp', 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(state, json_db, indent=4, ensure_ascii=False)

    os.rename(database_path, database_path + '.bak')
    os.rename(database_path + '.tmp', database_path)
    print('database updated. backup replaced.')


def make_db(db_json_dict_structure, database_path=db_path, debug=False):
    try:
        with open(database_path, 'r') as json_db:
            test = json.load(json_db)
            for k, v in db_json_dict_structure.items():
                if v == test[k]:
                    print(v)
                    print(test[k])
            if debug:
                print('db already made: ')
                db_print = json.dumps(test, indent=4, ensure_ascii=False)
                print("{} \n...{}chars".format(db_print[:1000], len(db_print)))
                print('-'*100)
            return json_db
    except KeyError:
        with open(database_path, 'w') as json_db:
            json.dump(db_json_dict_structure, json_db)
            print('new db constructed')


def adjust_db(database_path=db_path, max_capacity=10000, num_to_delete=30, debug=False):
    with open(database_path, 'r') as json_db:
        state_str = json_db.read()
        state = json.loads(state_str)
        if debug:
            print('current state')
            print(json.dumps(state, indent=4, ensure_ascii=False))
            print('replacing state (this is not redux yet)')

    # checking logic
    total_capacity = 0
    trends_cache = state['trends']['include_hashtags']



    # for tweets in state['trends']:
    #     tw_len = len(tweets['tweets'])
    #     total_tweets += tw_len
    #
    #     if debug:
    #         print('{} has {} tweets in db'.format(tweets['label'], tw_len))
    #
    # print('\ntotal tweets: {}'.format(total_tweets))
    #
    # if total_tweets <= max_capacity:
    #     print('images db within max capacity. not adjusting.')
    # else:
    #     print('images db close to over capacity. deleting 30 oldest trends')
    #     state['trends'] = state['trends'][num_to_delete:]
    # ---------------

    with open(database_path + '.tmp', 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(state, json_db, indent=4, ensure_ascii=False)

    os.rename(database_path, database_path + '.bak')
    os.rename(database_path + '.tmp', database_path)
    print('database updated. backup replaced.')


def adjust_images_db(database_path=img_db_path, max_capacity=65000, num_to_delete=30, debug=False):
    with open(database_path, 'r') as json_db:
        state_str = json_db.read()
        state = json.loads(state_str)
        if debug:
            print('current state')
            print(json.dumps(state, indent=4, ensure_ascii=False))
            print('replacing state (this is not redux yet)')

    # checking logic
    total_tweets = 0
    for tweets in state['trends']:
        tw_len = len(tweets['tweets'])
        total_tweets += tw_len

        if debug:
            print('{} has {} tweets in db'.format(tweets['label'], tw_len))

    print('\ntotal tweets: {}'.format(total_tweets))

    if total_tweets <= max_capacity:
        print('images db within max capacity. not adjusting.')
    else:
        print('images db close to over capacity. deleting 30 oldest trends')
        state['trends'] = state['trends'][num_to_delete:]
    # ---------------

    with open(database_path + '.tmp', 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(state, json_db, indent=4, ensure_ascii=False)

    os.rename(database_path, database_path + '.bak')
    os.rename(database_path + '.tmp', database_path)
    print('database updated. backup replaced.')


def adjust_top_posts_db(database_path=top_retweets_db_path, max_capacity=100000, num_to_delete=30, debug=False):
    with open(database_path, 'r') as json_db:
        state_str = json_db.read()
        state = json.loads(state_str)
        if debug:
            print('current state')
            print(json.dumps(state, indent=4, ensure_ascii=False))
            print('replacing state (this is not redux yet)')

    # checking logic
    total_tweets = len(state['top_posts'])

    print('\ntotal tweets: {}'.format(total_tweets))

    if total_tweets <= max_capacity:
        print('images db within max capacity. not adjusting.')
    else:
        print('images db close to over capacity. deleting 30 oldest trends')
        state['trends'] = state['trends'][num_to_delete:]
    # ---------------

    with open(database_path + '.tmp', 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(state, json_db, indent=4, ensure_ascii=False)

    os.rename(database_path, database_path + '.bak')
    os.rename(database_path + '.tmp', database_path)
    print('database updated. backup replaced.')


# MANUAL ONLY
def __split_db(database_path=db_path, second_database_path=img_db_path,  debug=False):
    from shutil import copyfile

    # load current db
    with open(database_path, 'r') as json_db:
        state_str = json_db.read()
        state = json.loads(state_str)
        if debug:
            print('current state')
            print(json.dumps(state, indent=4, ensure_ascii=False))
            print('replacing state (this is not redux yet)')

    # split trends from images

    second_db = {
        "trends": []
    }


    to_split = state['trends']['include_hashtags']
    for k, v in to_split.items():
        if k == "content":
            # content, timestamp, initial timestamp
            for ind, c in enumerate(v):
                # the content loop
                for l, w in c.items():
                    # in every content object, check for 'tweets' key
                    if l == "tweets":
                        # keep only tweets with rt_count
                        tweets_to_keep = []
                        for tw in w:
                            try:
                                if tw['retweet_count']:
                                    print('appending {}: rt_count: {}'.format(tw, tw['retweet_count']))
                                    tweets_to_keep.append(tw)
                            except:
                                continue

                        if len(tweets_to_keep) == 0:
                            continue

                        # throw tweets into db
                        second_db['trends'].append({
                            "label": c['label'],
                            "time": c['time'],
                            "tweets": tweets_to_keep
                        })
                # del tweets list from main dict
                try:
                    tw_print = len(state['trends']['include_hashtags']['content'][ind]['tweets'])
                    lbl_print = state['trends']['include_hashtags']['content'][ind]['label']
                    print('deleting {} tweets from {}'.format(tw_print, lbl_print))
                    del state['trends']['include_hashtags']['content'][ind]['tweets']
                except:
                    continue

            # print('test')
            # print(json.dumps(to_split, indent=4, ensure_ascii=False)[-5000:])
            # print('current content')
            # print(c)



    print(json.dumps(second_db, indent=4, ensure_ascii=False)[:100])
    print(len(second_db['trends']))


    total_tweets = 0
    for tweets in second_db['trends']:
        tw_len = len(tweets['tweets'])
        total_tweets += tw_len

        print('{} has {} tweets in db'.format(tweets['label'], tw_len))

    print('\ntotal tweets: {}'.format(total_tweets))

    # replace the include_hashtags values in current db
    #state['trends']['include_hashtags'] =

    # save current db
    db_original_name = database_path
    database_path = os.path.splitext(database_path)[0] + "_clean.json"
    copyfile(db_original_name, database_path)

    with open(database_path + '.tmp', 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(state, json_db, indent=4, ensure_ascii=False)

    os.rename(database_path, database_path + '.bak')
    os.rename(database_path + '.tmp', database_path)
    print('database updated. backup replaced.')

    # save image db
    with open(second_database_path + '.tmp', 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(second_db, json_db, indent=4, ensure_ascii=False)

    os.rename(second_database_path, second_database_path + '.bak')
    os.rename(second_database_path + '.tmp', second_database_path)
    print('database updated. backup replaced.')


if __name__ == "__main__":
    db_path = '../db/daily_databse.json'
    img_db_path = "../db/daily_trend_search_database.json"
    print(os.getcwd())
    __split_db(database_path=db_path, second_database_path=img_db_path)