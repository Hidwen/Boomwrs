import random
from wordfreq import top_n_list, zipf_frequency
from nltk.corpus import words

def main():
    print("Loading NLTK words...")
    nltk_words = words.words()
    
    # We only want lowercase words from NLTK to filter out names
    lowercase_nltk_words = set()
    for w in nltk_words:
        if w.islower() and w.isalpha():
            lowercase_nltk_words.add(w)

    print("Loading top words from wordfreq...")
    common_words = top_n_list('en', 30000)

    answers = []
    
    # Process for answers
    for word in common_words:
        if 2 <= len(word) <= 6:
            if word.isalpha():
                if word in lowercase_nltk_words:
                    score = zipf_frequency(word, 'en')
                    if score >= 3.5:
                        answers.append(word)

    # Process for valid words (guesses)
    # Valid guesses are answers + any lowercase NLTK word of 2 to 6 letters
    valid_words = set(answers)
    for word in lowercase_nltk_words:
        if 2 <= len(word) <= 6:
            if word.isalpha():
                valid_words.add(word)

    # Sort them for consistency
    answers.sort()
    valid_list = list(valid_words)
    valid_list.sort()

    print("Writing files...")
    # Write answers.txt
    with open("answers.txt", "w", encoding="utf-8") as f:
        for word in answers:
            f.write(word + "\n")

    # Write valid.txt
    with open("valid.txt", "w", encoding="utf-8") as f:
        for word in valid_list:
            f.write(word + "\n")

    # Print 40 random words per length
    print("Samples per length from answers:")
    for length in [2, 3, 4, 5, 6]:
        length_words = []
        for word in answers:
            if len(word) == length:
                length_words.append(word)
        
        sample_size = 40
        if len(length_words) < 40:
            sample_size = len(length_words)
            
        sample = random.sample(length_words, sample_size)
        print(f"Length {length}: {', '.join(sample)}")

if __name__ == "__main__":
    main()
