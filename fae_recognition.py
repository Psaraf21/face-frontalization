from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import face_recognition
import cv2
import numpy as np
import os
from io import BytesIO
from concurrent.futures import ProcessPoolExecutor
import uvicorn

app = FastAPI()

# Paths to the folder containing known faces
known_faces_dir = 'images'

# Paths to the folder containing known faces
# known_faces_dir = './known_faces'

# Initialize arrays to hold known face encodings and their corresponding names
known_face_encodings = []
known_face_names = []

# Load all known face images and their names
for filename in os.listdir(known_faces_dir):
    if filename.endswith(('.jpg', '.jpeg', '.png')):
        # Load the image and get face encoding
        image_path = os.path.join(known_faces_dir, filename)
        image = face_recognition.load_image_file(image_path)
        face_encodings = face_recognition.face_encodings(image)

        if face_encodings:  # Ensure that a face is detected
            face_encoding = face_encodings[0]  # Assume one face per image

            # Add the encoding and the name (from the file name without extension)
            known_face_encodings.append(face_encoding)
            known_face_names.append(os.path.splitext(filename)[0])

# Create a ProcessPoolExecutor for multiprocessing
executor = ProcessPoolExecutor()

def recognize_faces_in_image(image_data, known_face_encodings, known_face_names):
    # Convert the image data to a numpy array and then to an OpenCV image
    np_image = np.frombuffer(image_data, np.uint8)
    unknown_image = cv2.imdecode(np_image, cv2.IMREAD_COLOR)

    # Convert the image from BGR (OpenCV default) to RGB (face_recognition default)
    rgb_image = cv2.cvtColor(unknown_image, cv2.COLOR_BGR2RGB)

    # Find all face locations and encodings in the uploaded image
    face_locations = face_recognition.face_locations(rgb_image)
    unknown_face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

    # Iterate over each face found in the uploaded image
    for (top, right, bottom, left), face_encoding in zip(face_locations, unknown_face_encodings):
        # Compare the face encoding to known faces
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)
        name = "Unknown"

        # Use the first match found (or use a more sophisticated method)
        if True in matches:
            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]

        # Draw a bounding box around the face
        cv2.rectangle(unknown_image, (left, top), (right, bottom), (0, 255, 0), 2)

        # Draw a label with a name below the face
        cv2.rectangle(unknown_image, (left, bottom - 35), (right, bottom), (0, 255, 0), cv2.FILLED)
        font = cv2.FONT_HERSHEY_DUPLEX
        cv2.putText(unknown_image, name, (left + 6, bottom - 6), font, 0.8, (255, 255, 255), 1)

    # Convert the resulting image to a format that can be returned in the response
    _, buffer = cv2.imencode('.jpg', unknown_image)
    return buffer.tobytes()

@app.post("/recognize/")
async def recognize_face(image: UploadFile = File(...)):
    # Ensure the uploaded file is an image
    if image.content_type not in ["image/jpeg", "image/png"]:
        raise HTTPException(status_code=400, detail="Invalid image format")

    # Read the image file
    image_data = await image.read()

    # Use the executor to process the image in a separate process
    future = executor.submit(recognize_faces_in_image, image_data, known_face_encodings, known_face_names)
    result_image_data = future.result()

    # Return the resulting image as a streaming response
    return StreamingResponse(BytesIO(result_image_data), media_type="image/jpeg")
if _name_ == "_main_":
    uvicorn.run(app)