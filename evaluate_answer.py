import spacy

# Load Spacy NLP Model
nlp = spacy.load("en_core_web_sm")

def check_answer(question, correct_answer, keywords, client_answer, threshold=0.5):
    """
    Check if a client's answer is correct using minimal NLP (keywords + Jaccard similarity).
    
    Parameters:
    question (str): The question being asked
    correct_answer (str): The model correct answer
    keywords (list): List of important keywords that should be present
    client_answer (str): The client's answer
    threshold (float): Minimum Jaccard similarity score to be considered correct (default 0.5)
    
    Returns:
    str: "Correct" or "Incorrect"
    """

    # Check minimum length (at least 50 words)
    if len(client_answer.split()) < 50:
        return "Incorrect"

    # Extract words (lemmas) from the client answer
    client_tokens = {token.lemma_.lower() for token in nlp(client_answer) if token.is_alpha}
    correct_tokens = {token.lemma_.lower() for token in nlp(correct_answer) if token.is_alpha}

    # Compute Jaccard similarity
    intersection = client_tokens.intersection(correct_tokens)
    union = client_tokens.union(correct_tokens)
    similarity = len(intersection) / len(union) if union else 0

    # Check keywords
    keywords_found = sum(1 for keyword in keywords if keyword.lower() in client_tokens)
    keyword_ratio = keywords_found / len(keywords) if keywords else 0

    # Final score (70% similarity + 30% keyword match)
    final_score = (similarity * 0.7) + (keyword_ratio * 0.3)

    return "Correct" if final_score >= threshold else "Incorrect"

# Example usage:
if __name__ == "__main__":
    question = "Explain the process of photosynthesis."
    correct_answer = "Photosynthesis is the process by which plants convert light energy from the sun into chemical energy stored in glucose and other organic compounds. This process takes place in the chloroplasts, specifically using chlorophyll in the thylakoids. Carbon dioxide and water are converted into glucose and oxygen is released as a byproduct."
    keywords = ["light energy", "chemical energy", "plants", "chlorophyll", "glucose", "oxygen"]

    # Test with a good answer
    client_answer = "Photosynthesis is a biological process where plants harness light energy from the sun and convert it into chemical energy. This process occurs in the chloroplasts of plant cells, where chlorophyll captures sunlight. During photosynthesis, plants take in carbon dioxide and water, converting them into glucose while releasing oxygen into the atmosphere. This process is essential for life on Earth as it provides both food and oxygen."
    
    result = check_answer(question, correct_answer, keywords, client_answer)
    print(f"Student's answer is: {result}")

    # Test with a poor answer
    poor_answer = "Plants need sunlight to grow. They make food using sunlight."
    result = check_answer(question, correct_answer, keywords, poor_answer)
    print(f"Poor answer is: {result}")
