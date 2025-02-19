import streamlit as st
from PIL import Image
import subprocess
import tempfile
import os
import geocoder
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import glob
import pandas as pd
import easyocr
import cv2
import re

def sendMail(mail):
    g = geocoder.ip('me')
    CAMERA_LOCATION = g.json['address'] + f'. [Lat: {g.lat}, Lng:{g.lng}]'
    message = MIMEMultipart("alternative")
    message["Subject"] = 'Notification regarding e-challan fine'
    message["From"] = mail
    message["To"] = mail
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.ehlo()
    body = f'You were caught riding without helmet near {CAMERA_LOCATION}, and were fined Rupees 500. Please visit https://bit.ly/3QQxTRO to pay your due challan. If you are caught riding again without proper gear, you will be severely penalized.'
    message.attach(MIMEText(body, "plain"))
    server.login('otpsendermessage@gmail.com', 'tsqo mkan hqig ptsg')
    server.sendmail('otpsendermessage@gmail.com', mail, message.as_string())
    server.quit()

def get_last_created_folder(path):
    folders = [f for f in glob.glob(os.path.join(path, '*')) if os.path.isdir(f)]
    if not folders:
        print("No folders found in the specified path.")
        return None
    latest_folder = max(folders, key=os.path.getctime)
    return latest_folder

def image_upload_page():
    st.title("Image Upload Page")
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        st.image(image, caption='Uploaded Image.', use_column_width=True)



        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            image.save(tmp_file, format="JPEG")
            tmp_file_path = tmp_file.name

        process = subprocess.Popen([
            "python", "traffic-monitor.py", 
            "--source", tmp_file_path, 
            "--weights", "runs/train/exp/weights/best.pt", 
            "--save-crop"
        ])
        process.wait()

        BASE_DIR = get_last_created_folder('./runs/detect')
        try:
            BASE_DIR = BASE_DIR + '/crops/No-helmet'
            database = pd.read_csv('data.csv')

            warnedNums = []

            for path in os.listdir(BASE_DIR):
                path = os.path.join(BASE_DIR, path).replace('No-helmet', 'Numberplate')
                img = cv2.imread(path, 0)
                reader = easyocr.Reader(['en'])
                number = reader.readtext(img, mag_ratio=3)
                licensePlate = ""

                for i in range(len(number)):
                    for item in number[i]:
                        if type(item) == str:
                            licensePlate += item

                licensePlate = licensePlate.replace(' ', '')
                licensePlate = licensePlate.upper()
                licensePlate = re.sub(r'[^a-zA-Z0-9]', '', licensePlate)
                print('License number is:', licensePlate)

                if licensePlate not in warnedNums:
                    for index, plate in enumerate(database['Registration']):
                        if licensePlate == plate:
                            database.at[index, 'Due challan'] += 500
                            mail = database['Email'][index]
                            num = database['Phone number'][index]
                            sendMail(mail)
                            print(f"{database['Name'][index]} successfully notified!")
                            warnedNums.append(licensePlate)
                            database.to_csv(r'data.csv', index=False)
        except:
            print("Humans wearing helmets")

        os.remove(tmp_file_path)

    else:
        st.write("Please upload an image file.")



def registration_page():
    st.title("Registration Page")
    try:
        database = pd.read_csv('data.csv')
    except FileNotFoundError:
        database = pd.DataFrame(columns=['Name', 'Registration', 'Phone number', 'Email', 'Due challan'])
    st.subheader("Add or Update Records")
    name = st.text_input("Name")
    registration = st.text_input("Registration")
    phone = st.text_input("Phone Number")
    email = st.text_input("Email")
    due_challan = st.number_input("Due Challan", min_value=0)

    if st.button("Add/Update Record"):
        if name and registration and phone and email:
            if registration in database['Registration'].values:
                index = database[database['Registration'] == registration].index[0]
                database.at[index, 'Name'] = name
                database.at[index, 'Phone number'] = phone
                database.at[index, 'Email'] = email
                database.at[index, 'Due challan'] = due_challan
                st.success("Record updated successfully!")
            else:
                new_record = {
                    'Name': name,
                    'Registration': registration,
                    'Phone number': phone,
                    'Email': email,
                    'Due challan': due_challan
                }
                database = database.append(new_record, ignore_index=True)
                st.success("Record added successfully!")
            database.to_csv('data.csv', index=False)
        else:
            st.error("Please fill in all fields.")
            
def registration_details_page():
    st.title("Registration Details View Page")
    try:
        database = pd.read_csv('data.csv')
    except FileNotFoundError:
        st.error("No data found. Please add records in the Registration Page.")
        return
    st.write("Current Data:")
    st.dataframe(database)
    
def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox("Choose a page", ["Image Upload", "Registration", "Registration Details"])
    if page == "Image Upload":
        image_upload_page()
    elif page == "Registration":
        registration_page()
    elif page == "Registration Details":
        registration_details_page()
        
        
if __name__ == "__main__":
    main()