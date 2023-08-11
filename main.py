"""
    ===================================

    FACE RECOGNITION ATTENDANCE SYSTEM

    ===================================

    This is the main file for the face recognition attendance system.
    It contains the code for the GUI application.

    NOTE: 
        1. since all of the function are inside the same class, I did not break it into multiple files.
        2. the server_saveDataToNotion.js file must be running in the background for the attendance data to be saved to the server.
        3. you need to install node.js and run npm i from the root directory to install the required dependencies for the server.
        4. once the dependencies are installed, you can run the server using the command node server_saveDataToNotion.js
        
"""

# cv2 is the OpenCV library for image processing and computer vision
import cv2
# tkinter is the standard GUI library for Python
import tkinter as tk
# PIL is the Python Imaging Library
from PIL import Image, ImageTk
# face_recognition is a library for face recognition, it depends on dlib
import face_recognition
# os is a library for interacting with the operating system
import os
# numpy is a library for scientific computing
import numpy as np
# requests is a library for making HTTP requests
import requests
# messagebox is a module for displaying message boxes
from tkinter import messagebox
# ttk is a module for creating themed Tkinter widgets
import tkinter.ttk as ttk
# datetime is a module for manipulating dates and times
from datetime import datetime
# matplotlib is a library for creating graphs and charts
import matplotlib.pyplot as plt


# Create a class for the GUI application
class VideoStreamApp:
    def __init__(self, window):

        # self refers to the instance of the class
        self.window = window
        self.window.title("Video Stream App")

        # Create a label widget to display the video stream
        self.video_label = tk.Label(window)
        self.video_label.pack()

        # Create a button frame
        self.button_frame = tk.Frame(window)
        self.button_frame.pack(side=tk.TOP)

        # Create a button to get attendance records
        self.get_attendance_button = tk.Button(
            self.button_frame, text="Get attendance record", command=self.get_attendance_records)
        self.get_attendance_button.pack()

        # Create a frame for the attendance text and scrollbar
        self.attendance_frame = tk.Frame(window)
        self.attendance_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Create a text widget inside the frame for displaying attendance messages
        self.attendance_text = tk.Text(
            self.attendance_frame, height=10)
        self.attendance_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create a scrollbar for the attendance text widget
        self.attendance_scrollbar = tk.Scrollbar(
            self.attendance_frame)
        self.attendance_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Connect the scrollbar to the attendance text widget
        self.attendance_text.configure(
            yscrollcommand=self.attendance_scrollbar.set)
        self.attendance_scrollbar.configure(
            command=self.attendance_text.yview)

        # Create a frame for the unknown person message and button
        self.unknown_person_frame = tk.Frame(window)
        self.unknown_person_label = tk.Label(
            self.unknown_person_frame, text="Unknown person detected, do you want to register?")
        self.register_button = tk.Button(
            self.unknown_person_frame, text="Register", command=self.check_registration_eligibility)

        # Create the "known_faces" folder if it doesn't exist
        self.create_known_faces_folder()

        # Keep track of unknown person presence
        self.unknown_person_present = False

        # Load the known faces and their names
        self.load_known_faces()

        # Keep track of last attendance time for each student
        self.last_attendance_times = {}

        # Open the video capture
        self.cap = cv2.VideoCapture(1)
        self.cap.set(3, 640)
        self.cap.set(4, 480)

        # Create a list to store the number of students for which attendance was recorded
        self.attendance_counts = []

        # Start the video stream
        self.show_video_stream()

    # this function creates a folder for storing the known faces in current directory
    def create_known_faces_folder(self):
        if not os.path.exists("known_faces"):
            os.makedirs("known_faces")

    # this function loads the known faces and their names
    def load_known_faces(self):
        # Create empty lists for known faces and names

        self.known_faces = []
        self.known_names = []

        # Load known faces from the "known_faces" folder
        known_faces_folder = "known_faces"
        for file_name in os.listdir(known_faces_folder):
            image_path = os.path.join(known_faces_folder, file_name)
            image = face_recognition.load_image_file(image_path)
            face_encoding = face_recognition.face_encodings(image)[0]
            self.known_faces.append(face_encoding)
            self.known_names.append(os.path.splitext(file_name)[0])

    # this function fetches the last attendance times for all students
    def fetch_last_attendance_times(self):
        url = "http://localhost:3000/"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                attendance_data = response.json()
                for data in attendance_data:
                    student_name = data.get("studentName")
                    attendance_time = data.get("attendanceTime")
                    self.last_attendance_times[student_name] = attendance_time
            else:
                print("Failed to fetch last attendance times.")
        # except means if there is an exception, do the following
        except requests.exceptions.RequestException as e:
            print("Error occurred while fetching last attendance times:", e)

    # this function sends the attendance data to the server
    def send_attendance_data(self, student_name, attendance_time):
        url = "http://localhost:3000/save"
        data = {
            "studentName": student_name,
            "attendanceTime": attendance_time
        }
        try:
            # Send a POST request to the server
            response = requests.post(url, json=data)
            if response.status_code == 200:
                print("Attendance data sent successfully.")
                self.attendance_text.insert(
                    tk.END, f"Attendance marked for: {student_name}\n")
                # Scroll to the latest message
                self.attendance_text.see(tk.END)
                self.update_attendance_counts()
            else:
                print("Failed to send attendance data.")
        # except means if there is an exception, do the following
        except requests.exceptions.RequestException as e:
            print("Error occurred while sending attendance data:", e)

    # this function checks if attendance is allowed for a student at a given time, each student can mark attendance only once in 30 seconds (30 secconds for testing purposes)
    def is_attendance_allowed(self, student_name, current_time):
        last_attendance_time = self.last_attendance_times.get(student_name)
        if last_attendance_time:
            last_attendance_time = datetime.strptime(
                last_attendance_time, "%Y-%m-%d %H:%M:%S")
            current_time = datetime.strptime(current_time, "%Y-%m-%d %H:%M:%S")
            time_difference = current_time - last_attendance_time
            if time_difference.seconds < 30:
                return False
        return True

    # this function displays the video stream
    def show_video_stream(self):
        # Read a frame from the video capture
        ret, frame = self.cap.read()
        frame = cv2.flip(frame, 1)

        # Convert the frame from BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces in the frame
        face_locations = face_recognition.face_locations(frame_rgb)
        face_encodings = face_recognition.face_encodings(
            frame_rgb, face_locations)

        # Check if any face matches the known faces
        is_unknown_person_present = False
        for face_encoding, face_location in zip(face_encodings, face_locations):
            matches = face_recognition.compare_faces(
                self.known_faces, face_encoding)
            name = "Unknown"

            # If a match is found, get the corresponding name
            if True in matches:
                matched_indices = np.where(matches)[0]
                matched_names = [self.known_names[index]
                                 for index in matched_indices]
                name = ', '.join(matched_names)

                # Get current date and time
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if self.is_attendance_allowed(name, current_time):
                    self.send_attendance_data(name, current_time)
                    self.last_attendance_times[name] = current_time

            else:
                is_unknown_person_present = True

            # Increase the size of the bounding box
            top, right, bottom, left = face_location
            padding = 20
            top -= padding
            right += padding
            bottom += padding
            left -= padding

            # Draw a green box and display the name
            cv2.rectangle(frame_rgb, (left, top),
                          (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame_rgb, name, (left, top - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Convert the frame to PIL format
        img = Image.fromarray(frame_rgb)
        img = ImageTk.PhotoImage(image=img)

        # Update the video label with the new frame
        self.video_label.imgtk = img
        self.video_label.configure(image=img)

        # Check if unknown person is present and display the message and button accordingly
        if is_unknown_person_present:
            if not self.unknown_person_present:
                self.unknown_person_frame.pack(side=tk.TOP)
                self.unknown_person_label.pack()
                self.register_button.pack()
                self.unknown_person_present = True
        else:
            if self.unknown_person_present:
                self.unknown_person_frame.pack_forget()
                self.unknown_person_present = False

        # Schedule the next update after 10 milliseconds
        self.window.after(10, self.show_video_stream)

    # this function checks if the current frame contains only one unknown person and opens the registration window
    def check_registration_eligibility(self):
        # Detect faces in the current frame
        ret, frame = self.cap.read()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(frame_rgb)
        face_count = len(face_locations)

        # Check if only one unknown person is present for registration
        if face_count == 1:
            self.open_registration_window()
        else:
            messagebox.showinfo(
                "Registration", "Only one unregistered student allowed for the registration process.")

    # this function opens the registration window
    def open_registration_window(self):
        registration_window = tk.Toplevel(self.window)
        registration_window.title("Registration")

        # Create a label and entry field for student name
        student_name_label = tk.Label(
            registration_window, text="Student Name:")
        student_name_label.pack()

        student_name_entry = tk.Entry(registration_window)
        student_name_entry.pack()

        # Create buttons for Go Back and Next
        button_frame = tk.Frame(registration_window)
        button_frame.pack()

        go_back_button = tk.Button(
            button_frame, text="Go Back", command=registration_window.destroy)
        go_back_button.pack(side=tk.LEFT)

        next_button = tk.Button(button_frame, text="Next", command=lambda: self.start_photo_capture(
            registration_window, student_name_entry.get()))
        next_button.pack(side=tk.LEFT)

    # this function starts the photo capture process
    def start_photo_capture(self, registration_window, student_name):
        # destroy the registration window
        registration_window.destroy()

        photo_capture_window = tk.Toplevel(self.window)
        photo_capture_window.title("Photo Capture")

        # Create a label and button for photo capture
        photo_label = tk.Label(
            photo_capture_window, text="Capture Passport Size Photo")
        photo_label.pack()

        capture_button = tk.Button(
            photo_capture_window, text="Click Photo", command=lambda: self.capture_photo(photo_capture_window, student_name))
        capture_button.pack()

    # this function captures the passport size photo
    def capture_photo(self, photo_capture_window, student_name):
        # Capture the current frame
        ret, frame = self.cap.read()
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces in the current frame
        face_locations = face_recognition.face_locations(frame_rgb)
        face_count = len(face_locations)

        # Check if only one face is present in the current frame
        if face_count == 1:
            # Increase the size of the bounding box
            top, right, bottom, left = face_locations[0]
            padding = 20
            top -= padding
            right += padding
            bottom += padding
            left -= padding

            # Crop the face from the current frame
            face_image = frame_rgb[top:bottom, left:right]

            # Resize the cropped face image
            face_image = cv2.resize(face_image, (300, 300))

            # Convert the cropped face image to PIL format
            face_image = Image.fromarray(face_image)

            # Save the cropped face image
            file_name = student_name + ".jpg"
            file_path = os.path.join("known_faces", file_name)
            face_image.save(file_path)

        # Display a success message
        messagebox.showinfo(
            "Photo Capture", "Passport size photo captured successfully.")

        # Close the photo capture window
        photo_capture_window.destroy()

        # Reload the known faces
        self.load_known_faces()

    # this function updates the attendance counts
    def update_attendance_counts(self):
        attendance_count = len(self.last_attendance_times)
        self.attendance_counts.append(attendance_count)

    # this function fetches the attendance records from the server and displays them in a new window
    def get_attendance_records(self):
        url = "http://localhost:3000/"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                attendance_data = response.json()

                # Create a new window to display attendance records in tabular form
                window = tk.Toplevel()
                window.title("Attendance Records")

                # Create a treeview widget to display the attendance records
                # treeview is a widget which can display data in tabular form
                treeview = ttk.Treeview(window)
                treeview.pack()

                # Configure the treeview columns
                treeview['columns'] = ('student_name', 'attendance_time')
                treeview.column('student_name', width=150, anchor='center')
                treeview.column('attendance_time', width=150, anchor='center')

                # Set the headings for the treeview columns
                treeview.heading('student_name', text='Student Name')
                treeview.heading('attendance_time', text='Attendance Time')

                # Insert attendance data into the treeview
                for data in attendance_data:
                    student_name = data.get("studentName")
                    attendance_time = data.get("attendanceTime")
                    treeview.insert('', tk.END, values=(
                        student_name, attendance_time))

                # Create a graph for the number of students for which attendance was recorded
                self.create_attendance_graph()

            else:
                messagebox.showerror(
                    "Error", "Failed to fetch attendance records.")

        except requests.exceptions.RequestException as e:
            messagebox.showerror(
                "Error", f"Error occurred while fetching attendance records: {e}")

    # this function creates a graph for the number of students for which attendance was recorded
    def create_attendance_graph(self):
        # plt.plot() creates a line graph
        plt.plot(self.attendance_counts)
        # plt.xlabel() sets the label for the x-axis
        plt.xlabel("Attendance Record")
        # plt.ylabel() sets the label for the y-axis
        plt.ylabel("Number of Students")
        # plt.title() sets the title for the graph
        plt.title("Attendance Count")
        # plt.show() displays the graph
        plt.show()

    # this function runs the GUI application
    def run(self):
        self.fetch_last_attendance_times()
        self.window.mainloop()


# Create the Tkinter window
window = tk.Tk()

# Create an instance of the video stream app
app = VideoStreamApp(window)

# Run the application
app.run()

# Release the video capture and destroy the OpenCV windows
app.cap.release()
cv2.destroyAllWindows()
