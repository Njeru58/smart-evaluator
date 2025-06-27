from django.contrib import admin
import os
import json
import re
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
                    model_name="gemini-1.5-flash",
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

class StudentSubmissionInline(admin.TabularInline):
    model = StudentSubmission
    extra = 0
    readonly_fields = ("evaluated", "marks", "evaluated_at", "evaluation_feedback")
    fields = ("question", "topic", "answer", "marks", "evaluated", "evaluated_at", "evaluation_feedback")


@admin.register(StudentResponse)
class StudentResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "ai_response", "created_at", "total_marks", "evaluated")
    list_filter = ("evaluated", "created_at")
    search_fields = ("student__username", "ai_response__id")
    inlines = [StudentSubmissionInline]
    actions = ["evaluate_responses"]

    def total_marks(self, obj):
        return sum(sub.marks for sub in obj.submissions.all())
    total_marks.short_description = "Total Marks"

    def evaluate_responses(self, request, queryset):
        try:
            import os
            import google.generativeai as genai

            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                self.message_user(request, "GEMINI_API_KEY not set.", level=messages.ERROR)
                return

            genai.configure(api_key=api_key)
            total_evaluated = 0

            for student_response in queryset:
                unevaluated_submissions = student_response.submissions.filter(evaluated=False)

                for submission in unevaluated_submissions:
                    print(f"[Admin Eval] Evaluating {submission}...")
                    submission.evaluate()
                    total_evaluated += 1

                # Mark student_response as evaluated only if ALL are done
                if student_response.submissions.filter(evaluated=False).count() == 0:
                    student_response.evaluated = True
                    student_response.save()

            if total_evaluated:
                self.message_user(request, f"{total_evaluated} submissions evaluated successfully.", level=messages.SUCCESS)
            else:
                self.message_user(request, "All selected responses were already fully evaluated.", level=messages.INFO)

        except Exception as e:
            self.message_user(request, f"Error during evaluation: {e}", level=messages.ERROR)

    evaluate_responses.short_description = "Evaluate Only Unevaluated Submissions"      
    
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

from django.contrib import admin
from .models import (
    VirtualExperiment,
    ApparatusItem,
    TheoryImage,
    ExperimentStep,
    ExperimentQuestion
)

class ApparatusItemInline(admin.TabularInline):
    model = ApparatusItem
    extra = 1
    classes = ['tab', 'tab-apparatus']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" style="border-radius: 4px;" />', obj.image.url)
        return "(No image)"
    image_preview.short_description = "Preview"


class TheoryImageInline(admin.TabularInline):
    model = TheoryImage
    extra = 1
    classes = ['tab', 'tab-theory']
    readonly_fields = ['image_preview']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="100" style="border-radius: 4px;" />', obj.image.url)
        return "(No image)"
    image_preview.short_description = "Preview"


class ExperimentStepInline(admin.StackedInline):
    model = ExperimentStep
    extra = 1
    classes = ['tab', 'tab-steps']
    readonly_fields = ['image_preview']
    fields = ['step_number', 'instruction', 'image', 'image_preview', 'video', 'video_url']

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="120" style="border-radius: 4px;" />', obj.image.url)
        return "(No image)"
    image_preview.short_description = "Step Image"


class ExperimentQuestionInline(admin.TabularInline):
    model = ExperimentQuestion
    extra = 1
    classes = ['tab', 'tab-questions']
    fields = ['question_text', 'marks']

from .models import ExperimentReport, ReportEvaluation
# === Parent Admin with Tabs ===
@admin.register(VirtualExperiment)
class VirtualExperimentAdmin(admin.ModelAdmin):
    list_display = ['title', 'code', 'requires_report', 'requires_questions']
    search_fields = ['title', 'code']
    list_filter = ['requires_report', 'requires_questions']

    fieldsets = (
    ('Basic Info', {
        'fields': ('title', 'code', 'objective', 'theory', 'method_summary', 'video_url'),
    }),
    ('Requirements', {
        'fields': ('requires_report', 'requires_questions'),
    }),
)


    inlines = [
        ApparatusItemInline,
        TheoryImageInline,
        ExperimentStepInline,
        ExperimentQuestionInline
    ]

    class Media:
        css = {
            'all': ('admin/css/widgets.css',),  # Optional: add your custom CSS here
        }

# Inline for Questions
class ExperimentQuestionInline(admin.TabularInline):
    model = ExperimentQuestion
    extra = 1
    classes = ['tab', 'tab-questions']
    fields = ['question_text', 'marks']



from .models import (ExperimentAnswer, ExperimentReport )

class ExperimentAnswerInline(admin.TabularInline):
    model = ExperimentAnswer
    extra = 0  # No empty row unless you add manually
    readonly_fields = ('question', 'answer_text')  # Optional: make answers view-only

from django.utils.safestring import mark_safe

class ReportEvaluationInline(admin.StackedInline):
    model = ReportEvaluation
    can_delete = False
    readonly_fields = ('evaluator', 'evaluated_at', 'display_scores', 'total_score')
    extra = 0

    def display_scores(self, obj):
        if not obj or not obj.scores:
            return "No scores available"
        html = "<ul style='list-style:none;'>"
        for section, score in obj.scores.items():
            html += f"<li><strong>{section.title()}</strong>: {score}/10</li>"
        html += "</ul>"
        return mark_safe(html)
    display_scores.short_description = "Section Scores"

@admin.register(ExperimentReport)
class ExperimentReportAdmin(admin.ModelAdmin):
    list_display = ('experiment', 'student', 'submitted_at', 'total_score', 'evaluated_status')
    search_fields = ('experiment__title', 'student__username')
    list_filter = ('submitted_at',)
    inlines = [ExperimentAnswerInline, ReportEvaluationInline]
    actions = ['evaluate_reports']

    def evaluated_status(self, obj):
        return "✅" if hasattr(obj, 'evaluation') else "❌"
    evaluated_status.short_description = "Evaluated"

    def total_score(self, obj):
        if hasattr(obj, 'evaluation') and obj.evaluation.scores:
            return sum(obj.evaluation.scores.values())
        return "-"
    total_score.short_description = "Total Score"

    def evaluate_reports(self, request, queryset):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            self.message_user(request, "GEMINI_API_KEY environment variable not set.", level=messages.ERROR)
            return

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
        except Exception as config_error:
            self.message_user(request, f"Gemini configuration error: {config_error}", level=messages.ERROR)
            return

        evaluated = 0

        def truncate(text, limit=600):
            return (text[:limit] + '...') if text and len(text) > limit else text

        for report in queryset:
            try:
                prompt = f"""
You are an expert assistant evaluating a lab report. Assign a score (0-10) for each of these sections:

1. Objective: {truncate(report.objective)}
2. Theory: {truncate(report.theory)}
3. Apparatus Scope: {truncate(report.apparatus_scope)}
4. Procedure: {truncate(report.procedure)}
5. Results: {truncate(report.results)}
6. Data Analysis: {truncate(report.data_analysis)}
7. Discussion: {truncate(report.discussion)}
8. Conclusion: {truncate(report.conclusion)}
9. References: {truncate(report.references)}

Return a valid JSON dictionary like this:
{{
  "objective": 7,
  "theory": 9,
  "apparatus_scope": 8,
  ...
}}
"""

                response = model.generate_content(prompt)
                raw = response.text.strip()
                raw = re.sub(r"```(?:json)?(.*?)```", r"\1", raw, flags=re.DOTALL).strip()

                scores = json.loads(raw)

                ReportEvaluation.objects.update_or_create(
                    report=report,
                    defaults={
                        'scores': scores,
                        'evaluator': request.user,
                    }
                )
                evaluated += 1

            except json.JSONDecodeError as je:
                self.message_user(request, f"JSON error for report {report.id}: {je}", level=messages.ERROR)
            except Exception as e:
                self.message_user(request, f"Error evaluating report {report.id}: {e}", level=messages.ERROR)

        if evaluated:
            self.message_user(request, f"{evaluated} report(s) evaluated using Gemini AI.", level=messages.SUCCESS)

    evaluate_reports.short_description = "Evaluate Selected Reports"

