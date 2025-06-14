# smart_evaluator  || QuestionBank

## Description
QuestionBank is a Django-based application designed to streamline the process of managing and evaluating multiple-choice questions for educational purposes. The system enables an admin or lecturer to upload questions, generate new questions using an integrated AI logic, and manage them efficiently.

## Key Features
- **Admin Management**: Admins can upload multiple-choice questions directly or through CSV files.
- **AI Question Generation**: Integrated AI functionality to generate new questions automatically.
- **Multiple User Interfaces**: Distinct interfaces for admins and students to manage tasks efficiently.
- **Student Account Management**: Students can create accounts, log in, and view their personalized dashboard.
- **Timed Tests**: Students can take tests within an assigned time period, ensuring a controlled testing environment.
- **Response Evaluation**: Admins can evaluate student responses using an AI model for automated grading.
- **Result Tracking**: Students can view their results and feedback after test submissions.
- **Organized Data Storage**: Structured objects for managing questions, responses, attempts, and AI-generated content.

## Installation

To set up QuestionBank locally, follow these steps:

1. **Clone the repository**
    ```bash
    git clone https://github.com/yourusername/QuestionBank.git
    cd QuestionBank
    ```

2. **(Optional) Create a virtual environment**
    - It is recommended to create a virtual environment to manage dependencies.
    ```bash
    python -m venv myenv
    source myenv/bin/activate   # On Windows, use `myenv\Scripts\activate`
    ```

3. **Install the required dependencies**
    ```bash
    pip install django
    pip install --upgrade google-cloud-aiplatform
    pip install google-generativeai
    pip install pandas
    ```

4. **Set up the AI key for Gemini AI**
    - Visit [Google AI Studio](https://aistudio.google.com/app/apikey) to obtain your API key for Gemini AI.
    - Embed the API key in your system environment:
    ```bash
    $env:GEMINI_API_KEY = "your API key"
    ```
    - Verify the key is set correctly:
    ```bash
    echo $env:GEMINI_API_KEY
    ```

5. **Run the Django development server**
    ```bash
    python manage.py runserver
    ```
    - To allow access from other devices on your network:
    ```bash
    python manage.py runserver 0.0.0.0:8000
    ```
    - Share the link with students:
    ```http
    http://your_ip_address:8000
    ```

By following these steps, you can monitor the number of students taking the test and invigilate them accordingly.

## Usage

## Admin Usage

1. **Login to Admin Interface**
   - Navigate to the Django admin interface at `http://localhost:8000/admin` and log in using your superuser credentials.

2. **Admin Dashboard**
   - After logging in, you will see various objects:
     - **Question**: Upload multiple-choice questions, specifying the correct option and saving them.
     - **CustomUser**: Manage user accounts.
     - **Response**: View submitted answers.
     - **Attempt**: Track student test attempts.
     - **UploadedFile**: Upload CSV files containing questions, multiple choices, and correct answers.
     - **EvaluatorAI**: Create instances to generate questions using AI.
     - **AIResponse**: View generated questions organized by topic.
     - **GeneratedQuestion**: View generated questions in a list format.
     - **StudentResponse**: Access submitted answers for AI-generated questions for evaluation.

### Student Usage

1. **Account Creation**
   - Students must create an account to access the system.

2. **Login**
   - After creating an account, students can log in to their dashboard.

3. **Taking Tests**
   - Students will find rules to guide them before taking tests. They can attempt the test within the assigned time period.

4. **Viewing Results**
   - After submission, students can view their results and any feedback provided by the evaluation system.

## Contact Information

For questions or support, please contact me at [rayonoxx@gmail.com](mailto:rayonoxx@gmail.com).
All rights served 

