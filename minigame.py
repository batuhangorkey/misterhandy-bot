import random


def initialize(word_length):
    f = open("words.txt", 'r')
    global_list = []
    final_list = []
    words = []
    word = ""
    for var in f.readline():
        if var != ' ':
            word += var
        else:
            global_list.append(word)
            word = ""
    f.close()
    for word in global_list:
        if len(word) == word_length:
            words.append(word)
    if word_length < 15:
        word_list = random.sample(words, 10)
        correct_word = random.choice(word_list)
        for var in word_list:
            counter = 0
            k = 0
            for char in var:
                if char == correct_word[k]:
                    counter += 1
                k += 1
            final_list.append((var, counter))
        return final_list
    else:
        return 0
