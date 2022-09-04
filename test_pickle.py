import pickle

data = pickle.load(open('./fs.pickle', 'rb'))

for item in data:
    print(item)