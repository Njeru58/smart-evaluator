from django.urls import path
from django.views.generic import TemplateView
from . import views
app_name = 'bank'
urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('dashboard/', views.user_home, name='user_home'),
    path('logout/', views.logout_view, name='logout'),
    path('quiz/', views.generate_quiz, name='generate_quiz'),
    path('quiz/question/', views.quiz_question, name='quiz_question'),
    path('quiz/result/<int:attempt_id>/', views.quiz_result, name='quiz_result'),
    path('attempts/', views.list_attempts, name='list_attempts'),
    path('attempts/<int:attempt_id>/', views.view_attempt, name='view_attempt'),
    path('upload/', views.upload_file, name='upload_file'),
    path('upload/success/', TemplateView.as_view(template_name='bank/upload_success.html'), name='upload_success'),
    path('evaluated-responses/', views.evaluated_responses, name='evaluated_responses'),
    path('evaluator_ai/', views.evaluator_ai_view, name='evaluator_ai'),
    path('topic_questions/<int:ai_response_id>/', views.topic_questions_view, name='topic_questions'),
    path('submit_answers/', views.submit_answers_view, name='submit_answers'),

]
