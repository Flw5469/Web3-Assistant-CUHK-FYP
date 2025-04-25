import csv
import Levenshtein
from typing import List, Dict, Tuple, Optional

def load_dictionary(csv_path: str) -> List[Dict[str, str]]:
    """
    Load the dictionary from a CSV file into memory.
    
    Args:
        csv_path: Path to the CSV file containing Question, Answer, Source columns
        
    Returns:
        A list of dictionaries, each containing question, answer, and source
    """
    dictionary = []
    try:
        with open(csv_path, 'r', encoding='latin-1') as file:
            reader = csv.DictReader(file)
            for row in reader:
                dictionary.append({
                    'question': row['Question'],
                    'answer': row['Answer'],
                    'source': row['Source']
                })
        print(f"Loaded {len(dictionary)} entries from {csv_path}")
        return dictionary
    except Exception as e:
        print(f"Error loading dictionary: {e}")
        return []
    
csv_path = 'dictionary.csv'  # Replace with your actual CSV file path
dictionary = load_dictionary(csv_path)


def find_dictionary_answer(query_text: str) -> str:
    """
    Find the answer to the most similar question in the dictionary.
    
    Args:
        query_text: The query text to match against questions in the dictionary
        
    Returns:
        A dictionary containing the matched question, answer, source, and similarity score,
        or None if no match above the threshold is found
    """

    threshold: float = 0.4

    if not dictionary:
        return None
    
    best_match = None
    highest_ratio = 0.0
    
    for entry in dictionary:
        ratio = Levenshtein.ratio(query_text.lower(), entry['question'].lower())
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = entry
    
    if highest_ratio >= threshold:
        return best_match['answer']
    else:
        return ""

def main():
    # Example usage
    csv_path = 'dictionary.csv'  # Replace with your actual CSV file path
    dictionary = load_dictionary(csv_path)
    
    if not dictionary:
        print("No dictionary loaded. Exiting.")
        return
    
    # Interactive query mode
    print("Enter a query (or 'exit' to quit):")
    while True:
        query = input("> ")
        if query.lower() == 'exit':
            break
        
        result = find_answer(query, dictionary)
        if result:
            print(f"\nBest match ({result['similarity']:.2f} similarity):")
            print(f"Q: {result['question']}")
            print(f"A: {result['answer']}")
            print(f"Source: {result['source']}")
        else:
            print("No suitable match found.")
        print()

if __name__ == "__main__":
    main()