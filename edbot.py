import argparse
from typing import List, Dict
import json
from llama_cpp import Llama
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EdBot:
    def __init__(self, model_path: str = "customweights.gguf", max_words: int = 20, modes: Dict = None):
        self.model_path = model_path
        self.max_words = max_words
        self.modes = modes or {
            'evaluate': {
                'prompt': 'Describe the user’s answer compared to the correct answer as a review in max 20 words.',
                'temp': 0.2,
                'tokens': 50
            },
            'hint': {
                'prompt': 'Provide only one direct hint:',
                'temp': 0.3,
                'tokens': 100
            },
            'explain': {
                'prompt': 'Explain directly and concisely:',
                'temp': 0.2,
                'tokens': 500
            },
            'tutor': {
                'prompt': ('Provide a direct and concise response to client queries. '
                        'If the user explicitly asks for a test paper, generate it directly. '
                        'For general queries, provide a brief response. '
                        'Do not generate test papers unless explicitly requested.'),
                'temp': 0.5,
                'tokens': 700
            }



        }
        self.llm = self.load_model()

    def load_model(self) -> Llama:
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found: {self.model_path}")
        return Llama(
            model_path=self.model_path,
            n_ctx=4096,
            n_threads=4,
            verbose=False,
            chat_format="llama-2"
        )

    def generate_response(self, prompt: str, mode: str) -> str:
        mode_config = self.modes[mode]
        max_words = self.max_words if mode != 'tutor' else 200  # Allow longer responses

        system_msg = (f"You are a direct response bot. Never use greetings or confirmations. "
                    f"For test papers, generate them fully without introductions. "
                    f"Stay within {max_words} words unless a test is requested.")

        try:
            response = self.llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=mode_config['tokens'],
                temperature=mode_config['temp'],
                stop=["Sure,", "Of course,", "Let me", "I'll"]
            )
            return self._clean_response(response['choices'][0]['message']['content'].strip())
        except Exception as e:
            logger.error(f"Error: {e}")
            return f"Error: {e}"


    def _clean_response(self, text: str) -> str:
        """Ensure responses are not empty or cut off valid outputs."""
        cleanup_starts = ["Sure,", "Of course,", "Here's", "Okay,", "Well,"]

        lines = text.split('\n')
        lines = [line.strip() for line in lines if line.strip() and 
                not any(line.strip().startswith(start) for start in cleanup_starts)]
        
        # Ensure response isn't empty after cleaning
        return '\n'.join(lines) if lines else text


    def process(self, mode: str, question: str, correct_answer: str = None, 
                user_answer: str = None, keywords: List[str] = None, context: str = None, attachment: str = None) -> Dict:
        keywords = keywords or []
        base_prompt = f"Q: {question}\nKeys: {', '.join(keywords)}"
        
        if mode == 'evaluate':
            prompt = (f"{self.modes[mode]['prompt']}\n{base_prompt}\n"
                      f"Expected Answer: {correct_answer}\n"
                      f"User Answer: {user_answer}\n")
        elif mode == 'explain':
            context_str = f"\nContext: {context}" if context else ""
            prompt = f"{self.modes[mode]['prompt']}\n{base_prompt}{context_str}\nA: {correct_answer}"
        elif mode == 'tutor':
            attachment_str = f"\nAttachment: {attachment}" if attachment else ""
            prompt = f"{self.modes[mode]['prompt']}\n{base_prompt}{attachment_str}"
        else:
            prompt = f"{self.modes[mode]['prompt']}\n{base_prompt}"
            
        return {mode: self.generate_response(prompt, mode)}

def main():
    parser = argparse.ArgumentParser(description='EdBot')
    parser.add_argument('--mode', required=True, choices=['evaluate', 'hint', 'explain', 'tutor'],
                       help='Mode of operation')
    parser.add_argument('--question', required=True, help='The question to process')
    parser.add_argument('--correct-answer', help='The correct answer')
    parser.add_argument('--user-answer', help='The user\'s answer')
    parser.add_argument('--keywords', help='Comma-separated keywords')
    parser.add_argument('--context', help='Additional context')
    parser.add_argument('--attachment', help='Attachment content (if any)')
    parser.add_argument('--model-path', default="customweights.gguf",
                       help='Path to the model file')
    parser.add_argument('--max-words', type=int, default=20,
                       help='Maximum number of words in response')
    parser.add_argument('--config', type=str, help='JSON file with mode configurations')

    args = parser.parse_args()
    
    modes = None
    if args.config:
        with open(args.config) as f:
            modes = json.load(f)

    keywords = args.keywords.split(',') if args.keywords else []

    try:
        bot = EdBot(model_path=args.model_path, max_words=args.max_words, modes=modes)
        result = bot.process(
            mode=args.mode,
            question=args.question,
            correct_answer=args.correct_answer,
            user_answer=args.user_answer,
            keywords=keywords,
            context=args.context,
            attachment=args.attachment
        )
        print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2))

if __name__ == "__main__":
    main()