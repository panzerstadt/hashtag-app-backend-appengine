import json

db_path = './db/daily_database.json'


def load_db(database_path=db_path, debug=False):
    with open(database_path) as json_db:
        return json.loads(json_db.read())


def update_db(dict_in, database_path=db_path, debug=False):
    with open(database_path, 'r') as json_db:
        state_str = json_db.read()
        state = json.loads(state_str)
        if debug:
            print('current state')
            print(json.dumps(state, indent=4, ensure_ascii=False))
            print('replacing state (this is not redux yet)')

        for k, v in dict_in.items():
            state[k] = dict_in[k]

    with open(database_path, 'w') as json_db:
        if debug:
            print('saving state')
        json.dump(state, json_db, indent=4, ensure_ascii=False)


def make_db(db_json_dict_structure, database_path=db_path, debug=False):
    try:
        with open(database_path, 'r') as json_db:
            test = json.load(json_db)
            for k, v in db_json_dict_structure.items():
                if v == test[k]:
                    print(v)
                    print(test[k])
            if debug:
                print('db already made: ', test)
            return json_db
    except:
        with open(database_path, 'w') as json_db:
            json.dump(db_json_dict_structure, json_db)
            print('new db constructed')
