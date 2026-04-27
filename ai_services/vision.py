import torch
from transformers import CLIPProcessor, CLIPModel
from PIL import Image

class VisionClassifier:
    def __init__(self, model_id="openai/clip-vit-base-patch32"):
        """
        Uses OpenAI's CLIP model for Zero-Shot Classification.
        This means we don't need to train it on custom data; it understands 
        concepts like "pothole" or "garbage" naturally!
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        # Load the model and processor locally
        self.model = CLIPModel.from_pretrained(model_id).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_id)
        
        # The categories we care about mapping to the GHMC
        self.labels = [
            "a photo of a pothole on a road",
            "a photo of garbage dumped on the street",
            "a photo of a broken streetlight",
            "a photo of a normal street with no issues"
        ]

    def classify_image(self, image_path):
        """
        Given an image path, detects the most likely civic issue.
        """
        image = Image.open(image_path).convert("RGB")
        
        # Pre-process image and text labels
        inputs = self.processor(text=self.labels, images=image, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Run inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        # CLIP gives image-text similarity scores. We extract the probabilities.
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1).cpu().numpy()[0]
        
        # Find the highest probability label
        max_idx = probs.argmax()
        best_label = self.labels[max_idx]
        confidence = probs[max_idx]
        
        # Map back to a clean category mapping
        category_map = {
            "a photo of a pothole on a road": "Road Issue (Pothole)",
            "a photo of garbage dumped on the street": "Sanitation (Garbage)",
            "a photo of a broken streetlight": "Electrical (Streetlight)",
            "a photo of a normal street with no issues": "No clear issue detected"
        }
        
        return {
            "category": category_map[best_label],
            "confidence": round(float(confidence), 4),
            "all_scores": {self.labels[i]: float(probs[i]) for i in range(len(self.labels))}
        }
