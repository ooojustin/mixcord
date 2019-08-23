from pathlib import Path

# funcs to get item at index in a list, or first item in list
# both return 'None' if item doesnt exist
at_index = lambda l, i: l[i] if len(l) > i else None
get_first = lambda l: at_index(l, 0)

# https://stackoverflow.com/a/5891598/5699643
def num_suffix(d):
    return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

def get_positive_int(i):
    try: i = int(i)
    except: return None
    return i if i > 0 else None

def get_percentage_str(part, whole):
    quotient = float(part) / float(whole)
    percentage = quotient * 100
    return str(round(percentage, 2))

def read_all_text(file):
    file = open(file)
    return file.read()

def write_all_text(file, text):
    file = open(file, "w")
    file.write(text)
    file.close()

def get_file_name(path, include_extension = True):
    path = Path(path).resolve()
    return path.name if include_extension else path.stem
