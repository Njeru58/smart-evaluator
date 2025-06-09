from django.contrib import admin
import os
import google.generativeai as genai
from django.utils.html import format_html
from .models import Question, CustomUser, Response, Attempt, UploadedFile, EvaluatorAI, AIResponse, StudentResponse,  GeneratedQuestion, Snapshot, StudentResponse, StudentSubmission
from django.contrib import messages


admin.site.register(CustomUser, admin.ModelAdmin)
admin.site.register(Question)
admin.site.register(Response)
admin.site.register(Attempt)
admin.site.register(UploadedFile)

from django.contrib import admin


class GeneratedQuestionInline(admin.TabularInline):
    model = GeneratedQuestion
    extra = 0  # Show no extra blank forms

# Register AIResponseAdmin with inlines for GeneratedQuestion

@admin.register(AIResponse)
class AIResponseAdmin(admin.ModelAdmin):
    list_display = ('topic', 'evaluator_ai', 'duration_minutes', 'get_number_of_generated_questions')
    fields = ('evaluator_ai', 'topic', 'duration_minutes')
    readonly_fields = ('get_number_of_generated_questions',)
    inlines = [GeneratedQuestionInline]

    def get_number_of_generated_questions(self, obj):
        return obj.questions.count()
 
    get_number_of_generated_questions.short_description = "Number of Generated Questions"



# Register GeneratedQuestionAdmin
@admin.register(GeneratedQuestion)
class GeneratedQuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'ai_response', 'marks', 'category', 'created_at')
    list_filter = ('ai_response', 'category', 'created_at')

    def save_model(self, request, obj, form, change):
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            form.base_fields['ai_response'].initial = AIResponse.objects.first()
        return form


# Register EvaluatorAIAdmin with custom action
@admin.register(EvaluatorAI)
class EvaluatorAIAdmin(admin.ModelAdmin):
    list_display = ('user', 'topic', 'number_of_questions')
    search_fields = ('user__username', 'topic')
    actions = ['generate_questions']  # Register the custom action here

    def generate_questions(self, request, queryset):
        response_data = []

        try:
            # Retrieve API key from environment variables
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                return self.message_user(request, "GEMINI_API_KEY environment variable not set.", level='ERROR')

            # Configure the AI generation library
            genai.configure(api_key=api_key)

            for evaluator_ai_instance in queryset:
                topic = evaluator_ai_instance.topic
                number_of_questions = evaluator_ai_instance.number_of_questions
                prompt_instructions = evaluator_ai_instance.prompt_instructions

                # Configure generation parameters (example settings)
                generation_config = {
                    "temperature": 0.5,
                    "top_p": 0.85,
                    "top_k": 32,
                    "max_output_tokens": 8192,
                    "response_mime_type": "text/plain",
                }

                # Initialize the generative model
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro",
                    generation_config=generation_config,
                    system_instruction=prompt_instructions,
                )

                # Start a chat session with the generative model
                chat_session = model.start_chat(
                    history=[
                        {
                            "role": "user",
                            "parts": [f"generate {number_of_questions} questions on {topic} operation"],
                        }
                    ]
                )

                # Send a message to generate the questions
                response = chat_session.send_message("Please generate the questions.")
                generated_questions = response.text  # Assuming response.text contains the generated questions

                # Create AIResponse object
                ai_response = AIResponse.objects.create(
                    evaluator_ai=evaluator_ai_instance,
                    topic=topic,
                )

                # Create new GeneratedQuestion instances
                for question_text in generated_questions.split('\n'):
                    if question_text.strip():
                        GeneratedQuestion.objects.create(ai_response=ai_response, question_text=question_text.strip())

                response_data.append({
                    'topic': topic,
                    'number_of_questions': number_of_questions,
                    'prompt_instructions': prompt_instructions,
                    'generated_questions': generated_questions
                })

            self.message_user(request, "Questions generated and saved successfully.", level='SUCCESS')

        except Exception as e:
            self.message_user(request, f"An error occurred during question generation: {e}", level='ERROR')

        # Return the JSON response if needed
        # return JsonResponse(response_data, safe=False)

    generate_questions.short_description = "Generate Questions"
    
    
    
############################evaluator inline
class EvaluatedResponseInline(admin.TabularInline):
    model = StudentResponse
    extra = 0  # Show no extra blank forms by default

    readonly_fields = ('evaluate_response',)  # Define fields as needed

    def evaluate_response(self, instance):
        if instance.evaluated:
            return f"Marks: {instance.marks}"
        else:
            return "Response not evaluated yet."

    evaluate_response.short_description = "Evaluation"

# class StudentResponseAdmin(admin.ModelAdmin):
#     list_display = ('id', 'answer', 'marks', 'evaluated')
#     actions = ['evaluate_responses']  # Register the custom action here

#     def evaluate_responses(self, request, queryset):
#         response_data = []

#         try:
#             # Retrieve API key from environment variables
#             api_key = os.environ.get("GEMINI_API_KEY")
#             if not api_key:
#                 return self.message_user(request, "GEMINI_API_KEY environment variable not set.", level='ERROR')

#             # Configure the AI generation library
#             genai.configure(api_key=api_key)

#             for student_response in queryset:
#                 evaluation_message = student_response.evaluate()

#                 response_data.append({
#                     'response_id': student_response.id,
#                     'evaluation_message': evaluation_message,
#                     'marks': student_response.marks,
#                     'evaluated': student_response.evaluated
#                 })

#             self.message_user(request, "Responses evaluated successfully.", level='SUCCESS')

#         except Exception as e:
#             self.message_user(request, f"An error occurred during evaluation: {e}", level='ERROR')

#         # Optionally, return JSON response data
#         # return JsonResponse(response_data, safe=False)

#     evaluate_responses.short_description = "Evaluate Responses"

# # Register the StudentResponseAdmin with the StudentResponse model
class StudentSubmissionInline(admin.TabularInline):
    model = StudentSubmission
    extra = 0  # No extra empty forms
    readonly_fields = ("evaluated", "marks", "evaluated_at")  # Read-only fields

class StudentResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "ai_response", "created_at", "total_marks", "evaluated")
    list_filter = ("evaluated", "created_at")
    search_fields = ("student__username", "ai_response__id")
    inlines = [StudentSubmissionInline]  # Enables inline viewing of submitted answers
    actions = ["evaluate_responses"]  # Bulk evaluation action

    def evaluate_responses(self, request, queryset):
        response_data = []

        try:
            # Retrieve API key from environment variables
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                self.message_user(request, "GEMINI_API_KEY environment variable not set.", level=messages.ERROR)
                return

            # Configure the AI model
            genai.configure(api_key=api_key)

            for student_response in queryset:
                for submission in student_response.submissions.all():
                    evaluation_message = submission.evaluate()  # Calls the AI evaluation function
                    response_data.append({
                        'response_id': submission.id,
                        'evaluation_message': evaluation_message,
                        'marks': submission.marks,
                        'evaluated': submission.evaluated
                    })

                student_response.evaluated = True  # Mark the whole response as evaluated
                student_response.save()

            self.message_user(request, "Selected responses have been evaluated successfully.", level=messages.SUCCESS)

        except Exception as e:
            self.message_user(request, f"An error occurred during evaluation: {e}", level=messages.ERROR)

    evaluate_responses.short_description = "Evaluate Selected Responses"

admin.site.register(StudentResponse, StudentResponseAdmin)

# class StudentResponseAdmin(admin.ModelAdmin):
#     list_display = ('id', 'student', 'created_at', 'total_marks', 'evaluated')
#     inlines = [StudentSubmissionInline]  # Show submissions inside response admin
#     actions = ['evaluate_responses']

#     def evaluated(self, obj):
#         return all(sub.evaluated for sub in obj.submissions.all())
#     evaluated.boolean = True  # Show as a checkmark in admin

#     def evaluate_responses(self, request, queryset):
#         response_data = []

#         try:
#             # Retrieve API key from environment variables
#             api_key = os.environ.get("GEMINI_API_KEY")
#             if not api_key:
#                 self.message_user(request, "GEMINI_API_KEY environment variable not set.", level='ERROR')
#                 return

#             # Configure the AI generation library
#             genai.configure(api_key=api_key)

#             for student_response in queryset:
#                 for submission in student_response.submissions.all():
#                     evaluation_message = submission.evaluate()

#                     response_data.append({
#                         'response_id': submission.id,
#                         'evaluation_message': evaluation_message,
#                         'marks': submission.marks,
#                         'evaluated': submission.evaluated
#                     })

#             self.message_user(request, "Responses evaluated successfully.", level='SUCCESS')

#         except Exception as e:
#             self.message_user(request, f"An error occurred during evaluation: {e}", level='ERROR')

#     evaluate_responses.short_description = "Evaluate All Responses"

# admin.site.register(StudentResponse, StudentResponseAdmin)


class SnapshotAdmin(admin.ModelAdmin):
    list_display = ('user', 'exam_session', 'timestamp', 'image_preview')  # Columns in admin list view
    readonly_fields = ('image_preview',)  # Prevent accidental edits

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="150px" style="border-radius: 5px;" />', obj.image.url)
        return "(No Image)"

    image_preview.short_description = "Snapshot"

admin.site.register(Snapshot, SnapshotAdmin)

from .models import VirtualExperiment, ExperimentImage, ExperimentReport, ExperimentQuestion, ExperimentAnswer

# Existing inline for images
class ExperimentImageInline(admin.TabularInline):
    model = ExperimentImage
    extra = 1

# ✅ New inline for experiment questions
class ExperimentQuestionInline(admin.TabularInline):
    model = ExperimentQuestion
    extra = 1

@admin.register(VirtualExperiment)
class VirtualExperimentAdmin(admin.ModelAdmin):
    list_display = ('title', 'code')
    search_fields = ('title', 'code')
    list_filter = ('code',)
    inlines = [ExperimentImageInline, ExperimentQuestionInline]  # Attach both inlines here

class ExperimentAnswerInline(admin.TabularInline):
    model = ExperimentAnswer
    extra = 0  # No empty row unless you add manually
    readonly_fields = ('question', 'answer_text')  # Optional: make answers view-only

@admin.register(ExperimentReport)
class ExperimentReportAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'student', 'submitted_at')
    search_fields = ('experiment__title', 'student__username')
    list_filter = ('submitted_at',)
    inlines = [ExperimentAnswerInline]  