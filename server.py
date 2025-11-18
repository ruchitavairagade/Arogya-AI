import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, send_from_directory
from tensorflow.keras.models import load_model
import tensorflow as tf

# Initialize Flask app
app = Flask(__name__)

# Load the model and class names
model = load_model("herbal_remedy_model.h5")
class_names = np.load('class_names.npy', allow_pickle=True)

# Dictionary of medicinal properties for each herb (you can expand this)
herb_properties = {
    # Add your actual herb data here
    "Tulsi": {
        "scientific_name": "Ocimum sanctum",
        "uses": "Respiratory issues, stress, inflammation",
        "preparation": "Tea, tincture, or essential oil"
    },
    "Neem": {
        "scientific_name": "Azadirachta indica",
        "uses": "Skin conditions, blood purifier, antimicrobial",
        "preparation": "Paste, powder, or oil extract"
    }
    # Add more herbs as needed
}

# Default properties for unknown herbs
default_properties = {
    "scientific_name": "Not available",
    "uses": "Information not available",
    "preparation": "Information not available"
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Handle file upload
        if 'image' not in request.files:
            return jsonify({"error": "No image file provided"}), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({"error": "No image selected"}), 400

        # Process the image
        npimg = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(npimg, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Invalid image file"}), 400
            
        # Resize and preprocess
        img = cv2.resize(img, (128, 128)) / 255.0
        img = np.expand_dims(img, axis=0)
        
        # Make prediction
        pred = model.predict(img)
        class_idx = np.argmax(pred)
        confidence = float(np.max(pred) * 100)
        
        # Get predicted herb name
        herb_name = class_names[class_idx]
        
        # Get herb properties (or default if not available)
        properties = herb_properties.get(herb_name, default_properties)
        
        # Return prediction results
        return jsonify({
            "herb_name": str(herb_name),
            "confidence": f"{confidence:.2f}%",
            "scientific_name": properties["scientific_name"],
            "medicinal_uses": properties["uses"],
            "preparation": properties["preparation"]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Check if model file exists
    if not os.path.exists("herbal_remedy_model.h5"):
        print("Error: Model file 'herbal_remedy_model.h5' not found.")
        print("Please run the training script first.")
        exit(1)
        
    # Check if class names file exists
    if not os.path.exists("class_names.npy"):
        print("Error: Class names file 'class_names.npy' not found.")
        print("Please run the training script first.")
        exit(1)
        
    print("Starting Flask server for Medicinal Plant Classifier...")
    app.run(debug=True, host='0.0.0.0', port=5000)