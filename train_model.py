import os
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras.models import Sequential # type: ignore
from tensorflow.keras.layers import Dense, Dropout # type: ignore
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from tensorflow.keras.utils import to_categorical # type: ignore
from sklearn.feature_extraction.text import TfidfVectorizer

 
csv_file_path = "herbal_remedies_dataset.csv" 

 
if not os.path.exists(csv_file_path):
    print(f"CSV file not found at: {csv_file_path}")
    raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

# Load data  
print(f"Loading data from CSV file: {csv_file_path}")
df = pd.read_csv(csv_file_path)

#information about the dataset
print(f"Dataset shape: {df.shape}")
print(f"Dataset columns: {df.columns.tolist()}")
print(f"Sample data (first 3 rows):\n{df.head(3)}")
print("\n" + "="*50)
print("IMPORTANT: We will predict 'Plant Name' based on other herb properties")
print("If you want to predict something else, change the TARGET_COLUMN variable in the code")
print("="*50 + "\n")

 
TARGET_COLUMN = 'Plant Name'  

 
if TARGET_COLUMN not in df.columns:
    print(f"Target column '{TARGET_COLUMN}' not found in dataset.")
    print("Available columns:", df.columns.tolist())
    print("\nPlease enter the exact name of the column you want to predict.")
    print("Just type the column name and press Enter (e.g. 'Plant Name')")
    TARGET_COLUMN = input("Column to predict: ")

  
exclude_columns = [TARGET_COLUMN]
feature_columns = [col for col in df.columns if col not in exclude_columns]

print(f"Using {len(feature_columns)} features to predict {TARGET_COLUMN}")
print(f"Features: {feature_columns}")
 
df.fillna("Unknown", inplace=True)

# Split data into features and target
X = df[feature_columns]
y = df[TARGET_COLUMN]

 
unique_classes = y.nunique()
print(f"Number of unique {TARGET_COLUMN} values: {unique_classes}")

if unique_classes > 100:
    print(f"Warning: Large number of classes ({unique_classes}) may require more training data and time")

# Label encoding for the target variable
label_encoder = LabelEncoder()
encoded_y = label_encoder.fit_transform(y)
print(f"Sample of encoded labels: {encoded_y[:5]}")

# Saving class names
np.save('class_names.npy', label_encoder.classes_)
print(f"Saved {len(label_encoder.classes_)} class names")

# multi-class classification
y_one_hot = to_categorical(encoded_y)
categorical_cols = []
numerical_cols = []
text_cols = []

for col in feature_columns:
    
    if pd.api.types.is_numeric_dtype(df[col]):
        numerical_cols.append(col)
   
    elif df[col].nunique() < 20:
        categorical_cols.append(col)
  
    else:
        text_cols.append(col)

print(f"Categorical columns: {categorical_cols}")
print(f"Numerical columns: {numerical_cols}")
print(f"Text columns: {text_cols}")

# categorical data
encoded_categorical_features = pd.DataFrame()
for col in categorical_cols:
  
    dummies = pd.get_dummies(df[col], prefix=col, drop_first=False)
    encoded_categorical_features = pd.concat([encoded_categorical_features, dummies], axis=1)


encoded_numerical_features = pd.DataFrame()
if numerical_cols:
    scaler = StandardScaler()
    scaled_numerical = scaler.fit_transform(df[numerical_cols])
    encoded_numerical_features = pd.DataFrame(
        scaled_numerical, 
        columns=numerical_cols
    )

# Process text data
encoded_text_features = pd.DataFrame()
for col in text_cols:
    
    # Use TF-IDF for text features
    vectorizer = TfidfVectorizer(max_features=50)  # Limit features taki extra coloums avoid ho
    text_features = vectorizer.fit_transform(df[col].astype(str))
    text_feature_names = [f"{col}_{i}" for i in range(text_features.shape[1])]
    text_df = pd.DataFrame(text_features.toarray(), columns=text_feature_names)
    encoded_text_features = pd.concat([encoded_text_features, text_df], axis=1)

# Combine features
feature_dfs = []
if not encoded_categorical_features.empty:
    feature_dfs.append(encoded_categorical_features)
if not encoded_numerical_features.empty:
    feature_dfs.append(encoded_numerical_features)
if not encoded_text_features.empty:
    feature_dfs.append(encoded_text_features)

processed_features = pd.concat(feature_dfs, axis=1)

print(f"Processed features shape: {processed_features.shape}")

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    processed_features, y_one_hot, test_size=0.2, random_state=42
)

print(f"Training on {X_train.shape[0]} samples, validating on {X_test.shape[0]} samples")
print(f"Feature vector size: {X_train.shape[1]}")

# neural network model banaya for softmax
model = Sequential([
    Dense(256, activation='relu', input_shape=(X_train.shape[1],)),
    Dropout(0.3),
    Dense(128, activation='relu'),
    Dropout(0.3),
    Dense(64, activation='relu'),
    Dense(y_one_hot.shape[1], activation='softmax')
])

model.summary()

# Compile the model
model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)

# Train the model
print("\nStarting model training. This may take some time with a large dataset...")
history = model.fit(
    X_train, y_train,
    epochs=10,
    batch_size=32,
    validation_data=(X_test, y_test),
    verbose=1
)

# Evaluate the model
test_loss, test_acc = model.evaluate(X_test, y_test)
print(f"Test accuracy: {test_acc:.4f}")
print(f"Test accuracy: {test_acc*100:.2f}%")  # Show as percentage

# Define the callback class
class PercentageMetricsCallback(tf.keras.callbacks.Callback):
    def on_epoch_end(self, epoch, logs=None):
        # Convert metrics to percentage
        print(f"\nEpoch {epoch+1} metrics in percentage:")
        print(f"Training accuracy: {logs['accuracy']*100:.2f}%")
        print(f"Validation accuracy: {logs['val_accuracy']*100:.2f}%")

# Then use it in your model.fit:
history = model.fit(
    X_train, y_train,
    epochs=10,
    batch_size=32,
    validation_data=(X_test, y_test),
    verbose=1,
    callbacks=[PercentageMetricsCallback()]
)
        
# Save the model
model.save("herbal_remedy_text_model.h5")
print("Model saved as herbal_remedy_text_model.h5")

# Saving the preprocessing 
import pickle
preprocessing_info = {
    'feature_columns': feature_columns,
    'categorical_cols': categorical_cols,
    'numerical_cols': numerical_cols,
    'text_cols': text_cols,
    'label_encoder': label_encoder
}

with open('preprocessing_info.pkl', 'wb') as f:
    pickle.dump(preprocessing_info, f)
print("Preprocessing information saved to preprocessing_info.pkl")

print("\nTraining completed. Model is now ready to use.")
print(f"The model can predict {TARGET_COLUMN} based on other herb properties.")