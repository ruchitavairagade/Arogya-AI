import numpy as np
import pandas as pd
import pickle
import tensorflow as tf
from tensorflow.keras.models import load_model # type: ignore

def load_model_and_preprocessing():
    """Load the trained model and preprocessing information"""
    try:
        # Loading model
        model = load_model("herbal_remedy_text_model.h5")
        print("Model loaded successfully")
        
        # Loading preprocess
        with open('preprocessing_info.pkl', 'rb') as f:
            preprocessing_info = pickle.load(f)
        print("Preprocessing information loaded")
        
        # Loading class names
        class_names = np.load('class_names.npy', allow_pickle=True)
        print(f"Loaded {len(class_names)} class names")
        
        return model, preprocessing_info, class_names
    except Exception as e:
        print(f"Error loading model or preprocessing information: {e}")
        return None, None, None

def predict_for_new_data(input_data, model, preprocessing_info, class_names):
    """Make predictions for new herbal remedy data"""
    
    if isinstance(input_data, dict):
        input_df = pd.DataFrame([input_data])
    else:
        input_df = pd.DataFrame(input_data)
    
    # Extract preprocess
    feature_columns = preprocessing_info['feature_columns']
    categorical_cols = preprocessing_info['categorical_cols']
    numerical_cols = preprocessing_info['numerical_cols']
    text_cols = preprocessing_info['text_cols']
    label_encoder = preprocessing_info['label_encoder']
    
    # Fill missing values
    input_df.fillna("Unknown", inplace=True)
    

    for col in feature_columns:
        if col not in input_df.columns:
            print(f"Warning: Column '{col}' not found in input data. Adding with default value 'Unknown'")
            input_df[col] = "Unknown"
    
 
    print("\nWARNING: For a full implementation, all preprocessing transformers should be saved and reused")
    

    processed_features = pd.get_dummies(input_df[feature_columns])
    
    # Make prediction
    prediction = model.predict(processed_features)
    
    # Get top 3 predictions
    top_indices = np.argsort(prediction[0])[-3:][::-1]
    

    results = []
    for i in top_indices:
        results.append({
            'predicted_class': class_names[i],
            'confidence': float(prediction[0][i])
        })
    
    return results


if __name__ == "__main__":
    model, preprocessing_info, class_names = load_model_and_preprocessing()
    
    if model is not None:
        print("\n--- Herbal Remedy Prediction System ---")
        print("Enter information about an herb to get predictions")
        
      
        example_input = {}
        
        for col in preprocessing_info['feature_columns']:
            value = input(f"Enter {col} (or press Enter to skip): ")
            if value: 
                example_input[col] = value
        
        # Make prediction
        predictions = predict_for_new_data(example_input, model, preprocessing_info, class_names)
        
        # Display results
        print("\nPrediction Results:")
        for i, pred in enumerate(predictions):
            print(f"{i+1}. {pred['predicted_class']} (Confidence: {pred['confidence']:.2%})")