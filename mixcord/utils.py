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
