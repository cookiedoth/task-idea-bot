def readFile(path):
    with open(path, 'r', encoding="utf8") as myfile: #cp1251
        data = str(myfile.read())
        return data
