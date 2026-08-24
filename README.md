VictoryLibrary
#### Video Demo: https://youtu.be/ODeW2yje4jE
#### GitHub: rachidbr6 /https://github.com/rachidbr6
#### edX: rachidbr666 /https://profile.edx.org/u/rachidbr666
#### Location: [rabat,Morocco]
#### Date: [16/08/2025]
Description:

VictoryLibrary is a library management application that can be used both as a web application and as a standalone desktop program.
It allows users to organize their personal collection of books, track their reading progress, and manage their account through a simple and intuitive interface.

The application combines a Flask backend with a MySQL database, and it can be run in a browser or as a desktop app through PyWebview.

Features

Book Management

Add new books by providing the title, author, and total number of pages

View all books in a structured table

Update current reading progress by saving the last page reached

Remove books that are no longer needed

User Accounts

Register with email and password

Secure login system before accessing the library

Desktop Integration

Run the application as a desktop program with its own icon

Build an executable version using PyInstaller

Technologies

Frontend: HTML, CSS, Bootstrap 5

Backend: Flask (Python)

Database: MySQL

Desktop Mode: PyWebview and PyInstaller

File Structure
VICTLORYLIBRARY
│   app.py              # Main Flask application (routes, logic, DB operations)
│   launch.py           # Runs the application in web mode
│   library.sql         # MySQL schema for the database
│   README.md           # Project documentation
│   requirements.txt    # Python dependencies
│   run_desktop.py      # PyWebview launcher for desktop mode
│
├───static
│   ├───books           # (Optional) Storage for book-related files
│   ├───log.jpg
│   ├───logo.ico
│   ├───main.jpg
│   ├───regflat.jpg
│   ├───styles.css
│   └───styles1.css
│
└───templates
    │   index.html      # Main interface (book list, add/update/delete forms)
    │   login.html      # Login page
    │   register.html   # Registration page

Database Schema

The main table for storing books is defined as follows:

id – INT, primary key, auto-increment

title – VARCHAR, required

author – VARCHAR, optional

total_pages – INT, optional

current_page – INT, default 0

Design Decisions

Flask was selected for its simplicity and ease of integration with Python.

MySQL was chosen over SQLite to allow better scalability and stability.

Bootstrap 5 provides a clean and responsive design.

PyWebview was integrated so the application can run as a native desktop app, improving accessibility and user experience.

Aesthetic Choice: Victorian Vibe

VictoryLibrary is not only a functional project but also a reflection of a personal inspiration.
The application design is influenced by the Victorian era aesthetic—an atmosphere of refinement, elegance, and timeless passion for literature.
This stylistic choice aims to recreate the feeling of an old reading room, blending modern technology with a classical library vibe.

How to Run

Clone the repository:

git clone https://github.com/your-username/VICTLORYLIBRARY.git
cd VICTLORYLIBRARY


Install dependencies:

pip install -r requirements.txt


Import the database schema:

mysql -u your_user -p your_db < library.sql


Run in web mode:

python launch.py


Open http://127.0.0.1:5000 in your browser.

Run in desktop mode:

python run_desktop.py

Future Improvements

Add support for book cover uploads

Enable file uploads for digital books (PDF/EPUB)

Introduce categories or tags for organizing collections

Add reading statistics and history tracking

Extend multi-user functionality with separate libraries
