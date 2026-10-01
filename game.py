import random

ANSWERS = []
VALID_GUESSES = set()

def load_words():
    global ANSWERS, VALID_GUESSES
    if not ANSWERS:
        with open("answers.txt", "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    ANSWERS.append(word)
        
        with open("valid.txt", "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if word:
                    VALID_GUESSES.add(word)

def pick_word():
    # Weights for lengths: 3: 2, 4: 3, 5: 3, 6: 3
    lengths = [3, 4, 5, 6]
    weights = [2, 3, 3, 3]
    
    # Simple weighted random choice without importing external modules
    total_weight = sum(weights)
    r = random.randint(1, total_weight)
    
    chosen_length = 6
    running_total = 0
    for i in range(len(lengths)):
        running_total += weights[i]
        if r <= running_total:
            chosen_length = lengths[i]
            break
    
    candidates = []
    for word in ANSWERS:
        if len(word) == chosen_length:
            candidates.append(word)
            
    if not candidates:
        return random.choice(ANSWERS)
        
    return random.choice(candidates)

def score_guess(guess, answer):
    result = ["white"] * len(guess)
    working_answer = list(answer)
    
    # Pass 1: green (correct position)
    for i in range(len(guess)):
        if guess[i] == answer[i]:
            result[i] = "green"
            working_answer[i] = None # Remove from working copy
            
    # Pass 2: orange (wrong position)
    for i in range(len(guess)):
        if result[i] != "green":
            letter = guess[i]
            if letter in working_answer:
                result[i] = "orange"
                # Remove the first occurrence from working copy
                working_answer[working_answer.index(letter)] = None
                
    return result

def is_real_word(guess):
    if guess in VALID_GUESSES:
        return True
    if guess.endswith("s"):
        base_word = guess[:-1]
        if base_word in VALID_GUESSES:
            return True
    return False

def keyboard_colors(guesses, answer):
    colors = {}
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    for letter in alphabet:
        colors[letter] = "unused"
        
    for guess in guesses:
        scores = score_guess(guess, answer)
        for i in range(len(guess)):
            letter = guess[i]
            score = scores[i]
            current = colors.get(letter, "unused")
            
            # Upgrade rules: green > orange > white > unused
            if score == "green":
                colors[letter] = "green"
            elif score == "orange" and current != "green":
                colors[letter] = "orange"
            elif score == "white" and current not in ["green", "orange"]:
                colors[letter] = "white"
                
    return colors

if __name__ == "__main__":
    load_words()
    # Test cases
    print("Testing LEVEL vs HOTEL:", score_guess("level", "hotel"))
    print("Testing APPLE vs ALLEY:", score_guess("apple", "alley"))
    print("Testing HOTEL vs HOTEL:", score_guess("hotel", "hotel"))
