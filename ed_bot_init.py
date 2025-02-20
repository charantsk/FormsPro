# edbot_init.py
from llama_cpp import Llama
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_model(model_path: str = "llama-2-7b-chat.gguf") -> Llama:
    """Initialize and return the LLM model."""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    llm = Llama(
        model_path=model_path,
        n_ctx=4096,
        n_threads=4,
        verbose=False,
        chat_format="llama-2"
    )
    return llm

# Global variable to store the model
global_llm = None

def get_model(model_path: str = "llama-2-7b-chat.gguf") -> Llama:
    """Get or initialize the model."""
    global global_llm
    if global_llm is None:
        global_llm = initialize_model(model_path)
    return global_llm