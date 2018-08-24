from flask import Response


def textify(text_str):
    return Response(text_str, mimetype='text/html')


# ---------
# BAD HACKS
# ---------
# todo: holy shit this is some real crappy hack
def get_filepath(filepath_with_extension, debug=False):
    test = filepath_with_extension[0]
    if not test == '/':
        filepath_with_extension = '/' + filepath_with_extension
    if test == '.':
        filepath_with_extension = filepath_with_extension[2:]
    if debug: print('starting filepath', filepath_with_extension)

    try:
        with open(filepath_with_extension): pass
        return filepath_with_extension
    except FileNotFoundError:
        try:
            fp0 = '.' + filepath_with_extension
            if debug: print('fp0', fp0)
            with open(fp0): pass
            return fp0
        except FileNotFoundError:
            try:
                fp1 = '..' + filepath_with_extension
                if debug: print('fp1', fp1)
                with open(fp1): pass
                return fp1
            except FileNotFoundError:
                try:
                    fp2 = '../..' + filepath_with_extension
                    if debug: print('fp2', fp2)
                    with open(fp2): pass
                    return fp2
                except FileNotFoundError:
                    try:
                        fp3 = '../../..' + filepath_with_extension
                        if debug: print('fp3', fp3)
                        with open(fp3): pass
                        return fp3
                    except:
                        print('current workingdir: ', os.getcwd())
                        raise SystemError("file not found by traversing backwards 3 folders")