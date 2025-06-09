import random

import json

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
import pandas as pd

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from .forms import UserLoginForm, RegistrationForm, UploadFileForm
from .models import Question, Response, Attempt, UploadedFile, AIResponse, StudentResponse,GeneratedQuestion, StudentSubmission, VirtualExperiment, ExperimentReport
from .models import VirtualExperiment, ExperimentQuestion, ExperimentAnswer
from django.http import HttpResponse
from django.contrib import messages

from .forms import ExperimentReportForm

import base64
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from datetime import datetime
from django.urls import reverse
from .models import Snapshot



from .constants import *


app_name = 'bank'


def home(request):
    context = {}
    return render(request, 'bank/index.html', context=context)


@login_required()
def user_home(request):
    context = {'user': request.user}
    return render(request, 'bank/dashboard.html', context=context)


def login_view(request):
    title = "Login"
    form = UserLoginForm(request.POST or None)
    if form.is_valid():
        username = form.cleaned_data.get("username")
        password = form.cleaned_data.get("password")
        user = authenticate(username=username, password=password)
        login(request, user)
        return redirect('bank:user_home')
    return render(request, 'bank/login.html', {"form": form, "title": title})


def register(request):
    title = "Create account"

    form = RegistrationForm(request.POST)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return redirect('bank:login')

    context = {'form': form, 'title': title}
    return render(request, 'bank/registration.html', context=context)


def logout_view(request):
    logout(request)
    return redirect('bank:home')


def error_404(request, exception):
    data = {}
    return render(request, 'bank/error_404.html', data)


def error_500(request):
    data = {}
    return render(request, 'bank/error_500.html', data)


@login_required
def generate_quiz(request):
    user = request.user
    user_rating = user.rating

    if user_rating == 0:
        difficulty_range = (0, 1)
    else:
        difficulty_range = (user_rating * 0.9, user_rating * 1.1)

    questions = list(Question.objects.filter(difficulty__gte=difficulty_range[0], difficulty__lte=difficulty_range[1]))
    selected_questions = random.sample(questions, min(NUM_QUESTIONS_PER_TEST, len(questions)))

    if not selected_questions:
        return render(request, 'bank/dashboard.html', {'user': user, 'no_questions': True})

    request.session['quiz'] = {
        'question_ids': [q.question_id for q in selected_questions],
        'current_question_index': 0,
        'responses': [],
        'feedback': None,
        'last_question_answered': False,
        'selected_option': None
    }

    return redirect('bank:quiz_question')


@login_required
def quiz_question(request):
    quiz_data = request.session.get('quiz')
    if not quiz_data:
        return redirect('bank:generate_quiz')

    question_ids = quiz_data['question_ids']
    current_index = quiz_data['current_question_index']
    feedback = quiz_data.get('feedback')
    selected_option = quiz_data.get('selected_option')

    if current_index >= len(question_ids):
        attempt = Attempt.objects.create(user=request.user)
        correct_answers = 0
        for response_data in quiz_data['responses']:
            question = get_object_or_404(Question, question_id=response_data['question_id'])
            Response.objects.create(
                user=request.user,
                question=question,
                selected_option=response_data['selected_option'],
                is_correct=response_data['is_correct'],
                attempt=attempt
            )
            if response_data['is_correct']:
                correct_answers += 1

        # Adjust user rating based on performance
        user = request.user
        user.rating += round(correct_answers * RATING_INCREMENT, 2)
        user.rating -= round((NUM_QUESTIONS_PER_TEST - correct_answers) * RATING_DECREMENT, 2)
        user.rating = round(min(max(user.rating, MIN_RATING), MAX_RATING), 2)  # Ensure rating is within 0 and 5
        user.save()

        del request.session['quiz']
        return redirect('bank:quiz_result', attempt_id=attempt.attempt_id)

    question_id = question_ids[current_index]
    question = get_object_or_404(Question, question_id=question_id)
    last_question_answered = quiz_data.get('last_question_answered', False)

    if request.method == 'POST' and not last_question_answered:
        selected_option = request.POST.get('selected_option')
        if not selected_option:
            error_message = "Please select an option before submitting."
            return render(request, 'bank/play.html', {
                'question': question,
                'question_number': current_index + 1,
                'total_questions': len(question_ids),
                'error_message': error_message,
                'feedback': feedback,
                'selected_option': selected_option
            })
        selected_option = int(selected_option)
        is_correct = selected_option == question.correct_option
        correct_option_text = getattr(question, f'option{question.correct_option}')
        feedback = 'Correct!' if is_correct else f'Incorrect. The correct answer was {correct_option_text}.'

        quiz_data['responses'].append({
            'question_id': question_id,
            'selected_option': selected_option,
            'is_correct': is_correct
        })
        quiz_data['feedback'] = feedback
        quiz_data['last_question_answered'] = True
        quiz_data['selected_option'] = selected_option
        request.session['quiz'] = quiz_data

    elif request.method == 'POST' and last_question_answered:
        quiz_data['current_question_index'] += 1
        quiz_data['feedback'] = None
        quiz_data['last_question_answered'] = False
        quiz_data['selected_option'] = None
        request.session['quiz'] = quiz_data
        return redirect('bank:quiz_question')

    return render(request, 'bank/play.html', {
        'question': question,
        'question_number': current_index + 1,
        'total_questions': len(question_ids),
        'feedback': feedback,
        'selected_option': selected_option
    })


@login_required
def quiz_result(request, attempt_id):
    attempt = get_object_or_404(Attempt, attempt_id=attempt_id)
    responses = Response.objects.filter(attempt=attempt)
    correct_answers = responses.filter(is_correct=True).count()
    total_questions = responses.count()
    user_rating = round(request.user.rating, 2)
    return render(request, 'bank/quiz_result.html', {
        'responses': responses,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
        'attempt_id': attempt_id,
        'user_rating': user_rating,
    })


@login_required
def list_attempts(request):
    attempts = Attempt.objects.filter(user=request.user).order_by('-timestamp')
    attempt_data = []
    for attempt in attempts:
        responses = Response.objects.filter(attempt=attempt)
        correct_answers = responses.filter(is_correct=True).count()
        total_questions = responses.count()
        attempt_data.append({
            'attempt': attempt,
            'correct_answers': correct_answers,
            'total_questions': total_questions
        })
    return render(request, 'bank/list_attempts.html', {'attempt_data': attempt_data})


@login_required
def view_attempt(request, attempt_id):
    attempt = get_object_or_404(Attempt, attempt_id=attempt_id, user=request.user)
    responses = Response.objects.filter(attempt=attempt)
    correct_answers = responses.filter(is_correct=True).count()
    total_questions = responses.count()
    return render(request, 'bank/view_attempt.html', {
        'attempt': attempt,
        'responses': responses,
        'correct_answers': correct_answers,
        'total_questions': total_questions,
    })


def is_superuser(user):
    if not user.is_superuser:
        raise PermissionDenied
    return True


@user_passes_test(is_superuser)
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            # Save the uploaded file
            uploaded_file = UploadedFile.objects.create(user=request.user, file=file)
            file_path = uploaded_file.file.path

            # Load data from the file into the database
            if file.name.endswith('.csv'):
                df = pd.read_csv(file_path)
            elif file.name.endswith('.xlsx'):
                df = pd.read_excel(file_path)
            else:
                return render(request, 'bank/upload.html', {'form': form, 'error': 'Unsupported file format'})

            for index, row in df.iterrows():
                Question.objects.create(
                    question_text=row['Q'],
                    option1=row['A'],
                    option2=row['B'],
                    option3=row['C'],
                    option4=row['D'],
                    correct_option=ord(row['Correct_Position']) - ord('A') + 1,
                    difficulty=row['DIF [0-1]'],
                    type='multi'  # Default to 'multi', update as needed
                )

            return redirect('upload_success')
    else:
        form = UploadFileForm()
    return render(request, 'bank/upload.html', {'form': form})




def evaluator_ai_view(request):
    ai_responses = AIResponse.objects.all()  # Adjust this queryset as needed
    context = {'ai_responses': ai_responses}
    return render(request, 'bank/evaluator_ai.html', context)

def topic_questions_view(request, ai_response_id):
    """
    View for displaying an exam with dynamically set time limits.
    """
    ai_response = get_object_or_404(AIResponse, id=ai_response_id)
    
    context = {
        'ai_response': ai_response,
        'time_limit': ai_response.time_limit  # ✅ Pass time limit to template
    }
    return render(request, 'bank/topic_questions.html', context)

@login_required
def submit_answers_view(request):
    """
    Handles submission of student responses.
    """
    if request.method == 'POST':
        try:
            ai_response_id = request.POST.get('ai_response_id')
            ai_response = get_object_or_404(AIResponse, pk=ai_response_id)

            answers = request.POST.getlist('answers[]')
            question_ids = request.POST.getlist('question_ids[]')
            user = request.user

            # ✅ Validate data integrity
            if len(answers) != len(question_ids):
                return HttpResponse("Mismatch between answers and questions.", status=400)

            student_response, created = StudentResponse.objects.get_or_create(
                student=user,
                ai_response=ai_response
            )

            # ✅ Use bulk creation for efficiency
            submissions = [
                StudentSubmission(
                    student_response=student_response,
                    question=get_object_or_404(GeneratedQuestion, pk=qid),
                    topic=ai_response.topic,
                    answer=ans.strip()
                )
                for ans, qid in zip(answers, question_ids)
            ]
            StudentSubmission.objects.bulk_create(submissions)

            return render(request, 'bank/submit_success.html')

        except Exception as e:
            return HttpResponse(f'An error occurred: {str(e)}', status=500)

    return HttpResponse('Method not allowed', status=405)

@login_required
def evaluated_responses(request):
    student_responses = StudentResponse.objects.filter(student=request.user, submissions__evaluated=True).distinct()

    evaluated_data = []
    for response in student_responses:
        submissions = response.submissions.filter(evaluated=True)
        for submission in submissions:
            evaluated_data.append({
                'id': submission.id,
                'answer': submission.answer,
                'marks': submission.marks,
                'evaluated_at': submission.evaluated_at,
                'topic': submission.topic,  # ← changed this
                'max_marks': submission.question.marks,
            })

    context = {
        'evaluated_responses': evaluated_data,
    }
    return render(request, 'bank/evaluator_results.html', context)


def log_tab_switch(request):
    if request.method == "POST":
        data = json.loads(request.body)
        tab_switches = data.get("tabSwitchCount", 0)
        print(f"User switched tabs {tab_switches} times.")  # Debugging: Log in terminal
        return JsonResponse({"message": "Tab switch logged"}, status=200)

    return JsonResponse({"error": "Invalid request"}, status=400)



@csrf_exempt
def save_snapshot(request):
    if request.method == "POST" and request.FILES.get("snapshot"):
        snapshot_file = request.FILES["snapshot"]
        exam_session = request.POST.get("exam_session", "Unknown Session")

        # Assuming you want to link the snapshot to the logged-in user
        user = request.user if request.user.is_authenticated else None

        snapshot = Snapshot.objects.create(
            user=user,
            exam_session=exam_session,
            image=snapshot_file
        )

        return JsonResponse({"status": "success", "snapshot_id": snapshot.id})
    
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


from django.views.generic import ListView, DetailView
from .models import VirtualExperiment

class ExperimentListView(ListView):
    model = VirtualExperiment
    template_name = 'bank/experiment_list.html'
    context_object_name = 'experiments'

class ExperimentDetailView(DetailView):
    model = VirtualExperiment
    template_name = 'bank/experiment_detail.html'
    context_object_name = 'experiment'


@login_required
def submit_report(request, experiment_id):
    experiment = get_object_or_404(VirtualExperiment, pk=experiment_id)
    
    if request.method == 'POST':
        observation = request.POST.get('observation', '').strip()
        data = request.POST.get('data', '').strip()
        report_file = request.FILES.get('report_file')

        if observation and data:
            report = ExperimentReport.objects.create(
                experiment=experiment,
                student=request.user,
                observation=observation,
                data=data,
                report_file=report_file
            )
            return redirect(reverse('bank:experiment_list'))
        else:
            error = "Please fill in both observation and data fields."
            return render(request, 'bank/submit_report.html', {
                'experiment': experiment,
                'error': error,
                'observation': observation,
                'data': data,
            })
    else:
        return render(request, 'bank/submit_report.html', {'experiment': experiment})
    
@login_required
def submit_report(request, experiment_id):
    experiment = get_object_or_404(VirtualExperiment, id=experiment_id)
    questions = ExperimentQuestion.objects.filter(experiment=experiment)  # ✅ Fetch related questions

    if request.method == 'POST':
        form = ExperimentReportForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.experiment = experiment
            report.student = request.user
            report.save()

            # ✅ Handle submitted answers for experiment questions
            for question in questions:
                answer_key = f"question_{question.id}"
                answer_text = request.POST.get(answer_key)
                if answer_text:
                    ExperimentAnswer.objects.create(  # You need to define this model
                        report=report,
                        question=question,
                        answer_text=answer_text
                    )

            messages.success(request, f'Your report for "{experiment.title}" has been submitted successfully.')
            return redirect('bank:report_submitted', experiment_id=experiment.id)
    else:
        form = ExperimentReportForm()

    return render(request, 'bank/submit_report.html', {
        'form': form,
        'experiment': experiment,
        'questions': questions  # ✅ Inject questions into template
    })

@login_required
def report_submitted(request, experiment_id):
    experiment = get_object_or_404(VirtualExperiment, id=experiment_id)

    # Get the latest report submitted by this student for the experiment
    report = ExperimentReport.objects.filter(experiment=experiment, student=request.user).order_by('-submitted_at').first()
    if not report:
        messages.error(request, "No report found for this experiment.")
        return redirect('bank:experiment_list')

    # Get all questions for the experiment
    questions = ExperimentQuestion.objects.filter(experiment=experiment)

    # Get all answers for this student related to this experiment/report
    answer_qs = ExperimentAnswer.objects.filter(report=report)

    # Build dictionary {question_id: answer_text}
    answers = {answer.question.id: answer.answer_text for answer in answer_qs}

    context = {
        'experiment': experiment,
        'report': report,
        'questions': questions,
        'answers': answers,
    }

    return render(request, 'bank/report_submitted.html', context)
