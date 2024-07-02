import random


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.shortcuts import render
import pandas as pd

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from .forms import UserLoginForm, RegistrationForm, UploadFileForm
from .models import Question, Response, Attempt, UploadedFile, AIResponse, StudentResponse,GeneratedQuestion
from django.http import HttpResponse

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

# Evaluator ai student interface
# def evaluator_ai(request):
#     ai_responses = AIResponse.objects.all()
#     return render(request, 'bank/evaluator_ai.html', {'ai_responses': ai_responses})


def evaluator_ai_view(request):
    ai_responses = AIResponse.objects.all()  # Adjust this queryset as needed
    context = {'ai_responses': ai_responses}
    return render(request, 'bank/evaluator_ai.html', context)

def topic_questions_view(request, ai_response_id):
    ai_response = AIResponse.objects.get(id=ai_response_id)
    context = {'ai_response': ai_response}
    return render(request, 'bank/topic_questions.html', context)

@login_required
def submit_answers_view(request):
    if request.method == 'POST':
        try:
            ai_response_id = request.POST.get('ai_response_id')
            ai_response = AIResponse.objects.get(pk=ai_response_id)

            # Retrieve answers and question IDs
            answers = request.POST.getlist('answers[]')
            question_ids = request.POST.getlist('question_ids[]')

            # Get the current logged-in user
            user = request.user

            # Process each answer and save it as a StudentResponse
            for answer, question_id in zip(answers, question_ids):
                question = GeneratedQuestion.objects.get(pk=question_id)

                # Create a StudentResponse object for each question-answer pair
                student_response = StudentResponse.objects.create(
                    ai_response=ai_response,
                    question=question,
                    answer=answer,
                    user=user  # Include the logged-in user
                )

                # Optional: Print for debugging
                print(f"Saved StudentResponse: {student_response}")

            # Redirect to a success page or render a success message
            return HttpResponse('Answers submitted successfully!')

        except AIResponse.DoesNotExist:
            return HttpResponse('AI Response does not exist.', status=404)

        except GeneratedQuestion.DoesNotExist:
            return HttpResponse('Generated Question does not exist.', status=404)

        except Exception as e:
            return HttpResponse(f'An error occurred: {str(e)}', status=500)

    else:
        return HttpResponse('Method not allowed', status=405)

@login_required
def evaluated_responses(request):
    # Filter evaluated responses by the logged-in user
    evaluated_responses = StudentResponse.objects.filter(evaluated=True, user=request.user)
    
    # Debugging output
    print(f"Evaluated Responses for User {request.user.username}:")
    for response in evaluated_responses:
        print(f"ID: {response.id}, Answer: {response.answer}, Marks: {response.marks}")
    
    context = {
        'evaluated_responses': evaluated_responses
    }
    return render(request, 'bank/evaluator_results.html', context)