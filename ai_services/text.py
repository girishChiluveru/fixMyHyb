import torch
from transformers import pipeline

class TextAnalyzer:
    def __init__(self, use_local_llm=True):
        """
        Generates reports and categorizes text based on local ML.
        We use a lightweight instruction-tuned local LLM (TinyLlama) for this,
        meaning no API limits or costs.
        """
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"
        
        # TinyLlama is 1.1 Billion parameters - excellent for basic report generation
        # It can run on a laptop with 8GB RAM.
        self.model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        
        # Initialize the text generation pipeline
        self.pipe = pipeline(
            "text-generation", 
            model=self.model_id, 
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            device=None if torch.cuda.is_available() else self.device
        )

    def generate_report(self, category, user_description, vision_confidence=None):
        """
        Takes the raw inputs and asks the small local LLM to generate a professional
        GHMC summary and actionable steps.
        """
        # We craft a structured prompt suitable for TinyLlama's instruction format
        system_prompt = "You are a professional municipal assistant in Hyderabad (GHMC). Summarize civic complaints."
        
        user_prompt = f"""
Issue Category provided by Vision AI: {category}
User Description: {user_description}

Please write a brief, professional 2-sentence summary of the problem, and suggest one actionable step for the municipal team.
        """

        # Format for TinyLlama Chat template
        prompt = f"<|system|>\n{system_prompt}</s>\n<|user|>\n{user_prompt}</s>\n<|assistant|>\n"
        
        try:
            outputs = self.pipe(
                prompt,
                max_new_tokens=150,
                temperature=0.3,
                do_sample=True,
                pad_token_id=self.pipe.tokenizer.eos_token_id
            )
            
            # The model outputs the entire prompt + generated text. We just want the generated part.
            generated_text = outputs[0]["generated_text"]
            response_only = generated_text.split("<|assistant|>\n")[-1].strip()
            
            return {
                "success": True,
                "report": response_only
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "report": "Failed to generate report locally."
            }
