def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def read_all_text(file):
    file = open(file)
    return file.read()

def write_all_text(file, text):
    file = open(file, "w")
    file.write(text)
    file.close()
