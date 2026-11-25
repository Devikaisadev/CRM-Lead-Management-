# Mini CRM – Lead Management System

## About the Project
Mini CRM is a web-based Lead Management System developed using Python Flask and MySQL. It helps users manage customer information, track leads, and monitor their progress through different stages.

## Features
- User Registration and Login
- Dashboard with Lead Statistics
- Add, View, Update and Delete Leads
- Search Leads by Name, Email or Company
- Filter Leads by Status
- Manage Lead Status (New, Contacted, Interested, Converted, Lost)
- MySQL Database Integration

## Technologies Used
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Backend:** Python, Flask
- **Database:** MySQL


## Installation and Setup

1. Clone or download the project.
2. Open the project in PyCharm.
3. Create and activate a Python virtual environment.
4. Install dependencies:

   `pip install -r requirements.txt`

5. Create the MySQL database using `schema.sql`.
6. Configure your database credentials and Flask secret key in the `.env` file.

## Run the Application

Execute:

`python app.py`

Open your browser and visit:

`http://127.0.0.1:5000/`

## Database
The project uses MySQL database named `mini_crm` to store user accounts and lead information.

## Project Purpose
This project demonstrates the implementation of a basic CRM system using Flask, REST APIs and MySQL.
