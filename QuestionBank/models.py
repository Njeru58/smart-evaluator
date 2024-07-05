# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, User
import os
import google.generativeai as genai
from django.conf import settings
from django.utils import timezone

class CustomUser(AbstractUser):
    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.username


class Question(models.Model):
    MULTIPLE_CHOICE = 'multi'
    WORD_COMPLETION = 'word'
    QUESTION_TYPES = [
        (MULTIPLE_CHOICE, 'Multiple Choice'),
        (WORD_COMPLETION, 'Word Completion'),
    ]

    question_id = models.AutoField(primary_key=True)
    question_text = models.TextField()
    option1 = models.TextField(blank=True, null=True)  # Optional for word completion
    option2 = models.TextField(blank=True, null=True)  # Optional for word completion
    option3 = models.TextField(blank=True, null=True)  # Optional for word completion
    option4 = models.TextField(blank=True, null=True)  # Optional for word completion
    correct_option = models.IntegerField(blank=True, null=True)  # Optional for word completion
    difficulty = models.FloatField()
    type = models.CharField(max_length=5, choices=QUESTION_TYPES, default=MULTIPLE_CHOICE)

    def __str__(self):
        return self.question_text


class Attempt(models.Model):
    attempt_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attempt {self.attempt_id} by {self.user.username}"


class Response(models.Model):
    response_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_option = models.IntegerField(blank=True, null=True)  # Optional for word completion
    is_correct = models.BooleanField()
    timestamp = models.DateTimeField(auto_now_add=True)
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE)

    def __str__(self):
        return f"Response {self.response_id} by {self.user.username}"


def user_directory_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/uploads/<username>_<user_id>/<filename>
    return 'uploads/{0}_{1}/{2}'.format(instance.user.username, instance.user.pk, filename)


class UploadedFile(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to=user_directory_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.name} uploaded by {self.user.username} at {self.uploaded_at}"
    
class EvaluatorAI(models.Model):
    topic = models.CharField(max_length=100)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    number_of_questions = models.IntegerField()
    prompt_instructions = models.TextField()
    generated_questions = models.TextField(blank=True) 
    def __str__(self):
        return f"EvaluatorAI - {self.topic} - {self.user}"
    
  


class AIResponse(models.Model):
    evaluator_ai = models.ForeignKey(EvaluatorAI, on_delete=models.CASCADE, related_name='generated_responses')
    topic = models.CharField(max_length=100)

    def __str__(self):
        return f"AI Response for {self.topic}"

class GeneratedQuestion(models.Model):
    ai_response = models.ForeignKey(AIResponse, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()

    def __str__(self):
        return self.question_text[:50] 

##student response from ai
class StudentResponse(models.Model):
    ai_response = models.ForeignKey('AIResponse', on_delete=models.CASCADE)
    question = models.ForeignKey('GeneratedQuestion', on_delete=models.CASCADE)
    answer = models.TextField()
    marks = models.DecimalField(default=0.0, max_digits=5, decimal_places=2)
    evaluated = models.BooleanField(default=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    evaluated_at = models.DateTimeField(blank=True, null=True)  # New field for evaluation timestamp

    def __str__(self):
        return f"Response for {self.ai_response.topic} - Question ID: {self.question.id}"

    def evaluate(self):
        try:
            # Retrieve API key from environment variables
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return "GEMINI_API_KEY environment variable not set."

            # Configure the AI generation library
            genai.configure(api_key=api_key)

            # Initialize the generative model
            generation_config = {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }
            model = genai.GenerativeModel(
                model_name="gemini-1.5-pro",
                generation_config=generation_config,
                system_instruction="\nYou will begin by receiving the answers submitted by the student. Next, evaluate the content of each response by analyzing the accuracy, relevance, completeness, and clarity of the information provided. Based on this analysis, allocate marks for each question according to the quality of the response, using a predefined rubric or scoring guide to ensure consistent grading. After assigning marks to each question, sum these marks to determine the student's overall score. Optionally, generate feedback for each response to help the student understand their strengths and areas for improvement.",
            )

            # Start a chat session with the generative model
            chat_session = model.start_chat(history=[])
            
            # Send student response to model for evaluation
            response = chat_session.send_message(self.answer)

            # Example: Evaluate based on generated response (dummy logic)
            if "good" in response.text.lower():
                self.marks = 5.0
                evaluation_message = "Excellent response!"
            else:
                self.marks = 2.5
                evaluation_message = "Average response."

            self.evaluated_at = timezone.now()  # Store evaluation timestamp
            self.evaluated = True  # Mark as evaluated
            self.save()

            return evaluation_message  # Return evaluation message

        except Exception as e:
            return f"An error occurred during evaluation: {e}"