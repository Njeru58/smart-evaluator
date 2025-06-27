# models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, User
import os
import google.generativeai as genai
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import now 

class CustomUser(AbstractUser):
    user_id = models.AutoField(primary_key=True)  # Explicit primary key
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.username

    @property
    def id(self):
        """Ensures compatibility with Django's default behavior by aliasing user_id as id."""
        return self.user_id



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
    evaluator_ai = models.ForeignKey(
        EvaluatorAI, on_delete=models.CASCADE, related_name='generated_responses'
    )
    topic = models.CharField(max_length=100)
    duration_minutes = models.PositiveIntegerField(default=30)  # ✅ Ensure a default value
    time_limit = models.PositiveIntegerField(default=1800)  # ✅ Ensure time_limit exists

    def __str__(self):
        return f"AI Response for {self.topic} ({self.duration_minutes} min)"





class GeneratedQuestion(models.Model):
    ai_response = models.ForeignKey(AIResponse, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    marks = models.IntegerField(default=1)  # ✅ Added marks field
    category = models.CharField(max_length=50, default="General")  # ✅ Added category field
    created_at = models.DateTimeField(auto_now_add=True)  # ✅ Added timestamp

    def __str__(self):
        return self.question_text[:50]
 

class StudentResponse(models.Model):  
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="responses",
        null=True, blank=True  # Allow null values to prevent errors
    )  

    ai_response = models.ForeignKey(
        "AIResponse",  
        on_delete=models.CASCADE,  
        related_name="student_responses",
        null=True, blank=True  # Allow null values for AI response
    )  

    created_at = models.DateTimeField(default=now)  
    evaluated = models.BooleanField(default=False)
    total_marks = models.DecimalField(default=0.0, max_digits=5, decimal_places=2)

    def __str__(self):  
        return f"{self.student.username if self.student else 'Unknown'} - {self.created_at}"  

    def evaluate(self):
        for submission in self.submissions.all():
            submission.evaluate()
        self.total_marks = sum(sub.marks for sub in self.submissions.all())
        self.evaluated = True
        self.save()


class StudentSubmission(models.Model):
    student_response = models.ForeignKey(
        'StudentResponse', on_delete=models.CASCADE, related_name="submissions"
    )
    question = models.ForeignKey('GeneratedQuestion', on_delete=models.CASCADE)
    topic = models.CharField(max_length=255)
    answer = models.TextField()
    marks = models.DecimalField(default=0.0, max_digits=5, decimal_places=2)
    evaluation_feedback = models.TextField(blank=True, null=True, help_text="AI-generated feedback for this submission.")
    evaluated = models.BooleanField(default=False)
    evaluated_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.student_response.student.username} - {self.topic} - {self.marks} Marks"

    def evaluate(self):
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return "GEMINI_API_KEY environment variable not set."

            genai.configure(api_key=api_key)

            generation_config = {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 64,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }

            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                generation_config=generation_config,
                system_instruction=(
                "You are an exam evaluator. Read the student's answer and provide a brief, constructive evaluation in natural language. "
                "Identify what's good, and point out what is missing, unclear, or could be improved. "
                "Avoid scores or rubric labels. Respond in one or two sentences only."

                ),
            )

            chat_session = model.start_chat(history=[])

            # ✅ Debug log for transparency
            print(f"[Evaluating] Student: {self.student_response.student.username} | "
                  f"Topic: {self.topic} | Question: {self.question.question_text[:60]}...")

            response = chat_session.send_message(self.answer)

            evaluation_message = response.text
            rubric_marks = self._estimate_score_from_keywords(response.text)  # optional helper if you still want to assign marks


            self.marks = rubric_marks
            self.evaluation_feedback = evaluation_message  # ✅ Save feedback
            self.evaluated_at = timezone.now()
            self.evaluated = True
            self.save()

            return evaluation_message

        except Exception as e:
            print(f"[Error] Evaluation failed for {self}: {e}")
            return f"An error occurred during evaluation: {str(e)}"


    def _estimate_score_from_keywords(self, text):
            """
            Estimate marks based on presence of key evaluation keywords in the Gemini feedback.
            """
            total = 0
            if "correct" in text.lower():
                total += self.question.marks * 0.3
            if "relevant" in text.lower():
                total += self.question.marks * 0.3
            if "complete" in text.lower():
                total += self.question.marks * 0.2
            if "clear" in text.lower():
                total += self.question.marks * 0.2

            return min(total, self.question.marks)

    def _evaluate_response(self, response_text):
        accuracy_weight = self.question.marks * 0.3
        relevance_weight = self.question.marks * 0.3
        completeness_weight = self.question.marks * 0.2
        clarity_weight = self.question.marks * 0.2

        accuracy = self._evaluate_accuracy(response_text, accuracy_weight)
        relevance = self._evaluate_relevance(response_text, relevance_weight)
        completeness = self._evaluate_completeness(response_text, completeness_weight)
        clarity = self._evaluate_clarity(response_text, clarity_weight)

        total = accuracy + relevance + completeness + clarity
        total = min(total, self.question.marks)

        message = (
            f"Evaluation:\n"
            f"- Accuracy: {accuracy:.2f}/{accuracy_weight:.2f}\n"
            f"- Relevance: {relevance:.2f}/{relevance_weight:.2f}\n"
            f"- Completeness: {completeness:.2f}/{completeness_weight:.2f}\n"
            f"- Clarity: {clarity:.2f}/{clarity_weight:.2f}"
        )

        return message, total

    def _evaluate_accuracy(self, text, weight):
        return weight if "correct" in text.lower() else 0

    def _evaluate_relevance(self, text, weight):
        return weight if "relevant" in text.lower() else 0

    def _evaluate_completeness(self, text, weight):
        return weight if "complete" in text.lower() else 0

    def _evaluate_clarity(self, text, weight):
        return weight if "clear" in text.lower() else 0
          
        
class Snapshot(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    exam_session = models.CharField(max_length=255)
    image = models.ImageField(upload_to="snapshots/")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Snapshot of {self.user} - {self.exam_session} ({self.timestamp})"

class VirtualExperiment(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=50)
    objective = models.TextField(blank=True)
    theory = models.TextField(blank=True)
    method_summary = models.TextField(blank=True, help_text="Optional overview of the procedure.")
    video_url = models.URLField(blank=True, null=True)

    requires_report = models.BooleanField(default=True)
    requires_questions = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Virtual Experiment"
        verbose_name_plural = "Virtual Experiments"


class ApparatusItem(models.Model):
    experiment = models.ForeignKey(VirtualExperiment, on_delete=models.CASCADE, related_name='apparatus_items')
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='apparatus_items/')

    def __str__(self):
        return self.name


class TheoryImage(models.Model):
    experiment = models.ForeignKey(VirtualExperiment, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='theory_images/')
    description = models.CharField(max_length=255, blank=True)


class ExperimentStep(models.Model):
    experiment = models.ForeignKey(VirtualExperiment, on_delete=models.CASCADE)
    step_number = models.PositiveIntegerField()
    instruction = models.TextField()
    image = models.ImageField(upload_to='step_images/', blank=True, null=True)
    video = models.FileField(upload_to='step_videos/', blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="Optional external video link (e.g., Google Drive/YouTube)")

    class Meta:
        ordering = ['step_number']


class ExperimentQuestion(models.Model):
    experiment = models.ForeignKey(VirtualExperiment, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    marks = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"Question for {self.experiment.title}"

class ExperimentDraft(models.Model):
    experiment = models.ForeignKey('VirtualExperiment', on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    observation = models.TextField(blank=True, null=True)
    data = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='draft_uploads/', blank=True, null=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('experiment', 'student')  # One draft per experiment per student

    def __str__(self):
        return f"Draft for {self.experiment.title} by {self.student.username}"
    
class ExperimentReport(models.Model):
    experiment = models.ForeignKey('VirtualExperiment', on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # Structured report sections
    group_members = models.TextField("Group Members", help_text="List of group members who participated", blank=True, null=True)
    objective = models.TextField("Objective/Aim", blank=True, null=True)
    theory = models.TextField("Theory/Introduction", blank=True, null=True)
    apparatus_scope = models.TextField("Apparatus/Scope", blank=True, null=True)
    procedure = models.TextField("Procedure/Method", blank=True, null=True)
    results = models.TextField("Results/Raw Data", blank=True, null=True)
    data_analysis = models.TextField("Data & Error Analysis", blank=True, null=True)
    discussion = models.TextField("Discussion", blank=True, null=True)
    conclusion = models.TextField("Conclusion", blank=True, null=True)
    references = models.TextField("References", blank=True, null=True)

    # Pre-filled and attached
    observation = models.TextField("Observation")
    data = models.TextField("Data Collected")
    report_file = models.FileField("Attach Report File", upload_to='experiment_reports/', blank=True, null=True)

    # Link to draft (if any)
    draft_used = models.OneToOneField(
        'ExperimentDraft',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='final_report',
        help_text="Draft that was used to submit this report, if applicable."
    )

    # ✅ Graph input fields
    graph_x_values = models.TextField(
        "X-Axis Values",
        blank=True,
        null=True,
        help_text="Comma-separated list of X values (e.g., 1, 2, 3, 4)"
    )
    graph_y_values = models.TextField(
        "Y-Axis Values",
        blank=True,
        null=True,
        help_text="Comma-separated list of Y values (e.g., 10, 20, 30, 40)"
    )

    # Optional: Advanced graph storage (use only if you're using PostgreSQL)
    # graph_data_json = JSONField(
    #     blank=True,
    #     null=True,
    #     help_text="Structured JSON of graph datasets"
    # )

    submitted_at = models.DateTimeField("Submitted At", null=True, blank=True)

    def __str__(self):
        return f"{self.experiment.title} - {self.student.username}"
    
    
class ExperimentAnswer(models.Model):
    report = models.ForeignKey(ExperimentReport, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ExperimentQuestion, on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return f"Answer by {self.report.student.username} to: {self.question.question_text[:30]}"

class ReportEvaluation(models.Model):
    report = models.OneToOneField("ExperimentReport", on_delete=models.CASCADE, related_name="evaluation")
    scores = models.JSONField()
    evaluator = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def total_score(self):
        return sum(self.scores.values())

    def __str__(self):
        return f"Evaluation for {self.report.student} - {self.report.experiment}"
