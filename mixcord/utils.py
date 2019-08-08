# https://stackoverflow.com/a/5891598/5699643
def day_suffix(d):
    return 'th' if 11<=d<=13 else {1:'st',2:'nd',3:'rd'}.get(d%10, 'th')

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
