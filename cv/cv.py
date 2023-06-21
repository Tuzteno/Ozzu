from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image, UnidentifiedImageError
from transformers import YolosImageProcessor, YolosForObjectDetection
import requests
import torch

app = FastAPI()

# Load the pretrained YOLOs-tiny model and its processor
model = YolosForObjectDetection.from_pretrained('hustvl/yolos-tiny')
processor = YolosImageProcessor.from_pretrained("hustvl/yolos-tiny")

@app.post("/detect")
async def detect_objects(image: UploadFile = File(...)):
    try:
        # Read the image file
        img = Image.open(image.file).convert("RGB")
    except UnidentifiedImageError:
        raise HTTPException(status_code=400, detail="Invalid image file.")
    except Exception as e:
        raise HTTPException(status_code=500, detail="An error occurred while reading the image file.")

    # Preprocess the image
    inputs = processor(images=img, return_tensors="pt")

    # Perform object detection
    outputs = model(**inputs)

    # Post-process the predictions
    target_sizes = torch.tensor([img.size[::-1]]) # The model expects target_sizes in the format (height, width)
    results = processor.post_process_object_detection(outputs, threshold=0.9, target_sizes=target_sizes)[0]
    
    processed_results = []
    for score, label, box in zip(results["scores"], results["labels"], results["boxes"]):
        box = [round(i, 2) for i in box.tolist()]
        processed_results.append({
            "label": model.config.id2label[label.item()],
            "confidence": round(score.item(), 3),
            "box": box
        })

    return {"results": processed_results}
