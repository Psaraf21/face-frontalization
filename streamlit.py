import streamlit as st
import pymongo
import bcrypt
import cloudinary
import cloudinary.uploader
import os
import numpy as np
from PIL import Image
# import face_recognition


client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["face_frontalization_db"]
users_collection = db["users"]



cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def find_user_by_username(username):
    return users_collection.find_one({"username": username})

def add_user(username, hashed_password, role):
    users_collection.insert_one({
        "username": username,
        "password": hashed_password,
        "role": role,
        "images": []
    })

def delete_user_by_username(username):
    users_collection.delete_one({"username": username})

def upload_to_cloudinary(image_bytes):
    return cloudinary.uploader.upload(image_bytes, resource_type="image")


def add_image_details(username, image_url, name, age, place, crime, phone):
    users_collection.update_one(
        {"username": username},
        {"$push": {
            "images": {
                "image_url": image_url,
                "name": name,
                "age": age,
                "place": place,
                "crime": crime,
                "phone": phone
            }
        }}
    )

def find_matching_image(uploaded_encoding):
    users = users_collection.find()
    for user in users:
        for stored_image in user.get("images", []):
            stored_encoding = np.array(stored_image.get("encoding", []))
            if stored_encoding.size and face_recognition.compare_faces([stored_encoding], uploaded_encoding)[0]:
                return user, stored_image
    return None, None


def signup():
    st.title("Signup")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    role = st.selectbox("Role", ["Officer", "Admin", "Administrator"])

    if st.button("Signup"):
        if find_user_by_username(username):
            st.error("Username already exists!")
        else:
            hashed_password = hash_password(password)
            add_user(username, hashed_password, role)
            st.success("Signup successful!")
            st.session_state["username"] = username
            st.session_state["role"] = role
            st.session_state["logged_in"] = True

def login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = find_user_by_username(username)
        if user and check_password(password, user["password"]):
            st.session_state["username"] = username
            st.session_state["role"] = user["role"]
            st.session_state["logged_in"] = True
            st.success(f"Welcome {username}!")
        else:
            st.error("Invalid username or password!")


def admin_dashboard():
    st.title("Admin Dashboard")
    uploaded_image = st.file_uploader("Upload Image")

    if uploaded_image:
       
        uploaded_image_bytes = uploaded_image.read()

        
        if uploaded_image_bytes:
            
            upload_result = upload_to_cloudinary(uploaded_image_bytes)
            image_url = upload_result.get("url")

            name = st.text_input("Name")
            age = st.text_input("Age")
            place = st.text_input("Place")
            crime = st.text_input("Crime")
            phone = st.text_input("Phone Number")

            if st.button("Submit"):
                add_image_details(
                    st.session_state["username"],
                    image_url,
                    name,
                    age,
                    place,
                    crime,
                    phone
                )
                st.success("Details submitted successfully!")
        else:
            st.error("Uploaded file is empty. Please try again.")



def officer_dashboard():
    st.title("Officer Dashboard")
    uploaded_image = st.file_uploader("Upload Image")

    if uploaded_image:
        img = Image.open(uploaded_image)
        img_array = np.array(img)

        
        uploaded_encoding = face_recognition.face_encodings(img_array)
        if uploaded_encoding:
            uploaded_encoding = uploaded_encoding[0]

            
            user, stored_image = find_matching_image(uploaded_encoding)
            if user:
                st.success(f"Match found: {stored_image['name']}, Age: {stored_image['age']}")
                st.write(f"Place: {stored_image['place']}, Crime: {stored_image['crime']}, Phone: {stored_image['phone']}")
                st.image(stored_image["image_url"], caption=f"Matched Image")
            else:
                st.warning("No match found.")


def administrator_panel():
    st.title("Administrator Panel")
    st.subheader("Manage Users")

    
    st.write("### Add User")
    username = st.text_input("New Username")
    password = st.text_input("New Password", type="password")
    role = st.selectbox("Role", ["Officer", "Admin"])

    if st.button("Add User"):
        if find_user_by_username(username):
            st.error("Username already exists!")
        else:
            hashed_password = hash_password(password)
            add_user(username, hashed_password, role)
            st.success("User added successfully!")

    
    st.write("### Remove User")
    remove_username = st.text_input("Username to Remove")
    if st.button("Remove User"):
        if find_user_by_username(remove_username):
            delete_user_by_username(remove_username)
            st.success(f"User {remove_username} removed successfully!")
        else:
            st.error("Username not found!")


def main():
    st.sidebar.title("SuspectSight")
    st.sidebar.title("Navigation")
    if "logged_in" not in st.session_state or not st.session_state["logged_in"]:
        options = st.sidebar.radio("Go to", ["Login", "Signup"])
        if options == "Login":
            login()
        elif options == "Signup":
            signup()
    else:
        st.sidebar.write(f"Logged in as {st.session_state['username']} ({st.session_state['role']})")
        if st.session_state["role"] == "Admin":
            admin_dashboard()
        elif st.session_state["role"] == "Officer":
            officer_dashboard()
        elif st.session_state["role"] == "Administrator":
            administrator_panel()
        if st.sidebar.button("Logout"):
            st.session_state.clear()
            st.sidebar.write("Logged out successfully!")

if _name_ == "_main_":
    main()