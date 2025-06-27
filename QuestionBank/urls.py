from django.urls import path
from django.views.generic import TemplateView
from . import views
from .views import log_tab_switch
from .views import save_snapshot
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
    path("log-tab-switch/", log_tab_switch, name="log_tab_switch"),
    path("save_snapshot/", views.save_snapshot, name="save_snapshot"),
    path('experiment_list/', views.ExperimentListView.as_view(), name='experiment_list'),
    # path('<int:pk>/', views.ExperimentDetailView.as_view(), name='experiment_detail'),
    # urls.py
    path('<int:pk>/', views.experiment_detail, name='experiment_detail'),

    path('experiment/<int:experiment_id>/auto_save_draft/', views.auto_save_draft, name='auto_save_draft'),
    path('experiment/<int:experiment_id>/submit_report/', views.submit_report, name='submit_report'),
    path('experiment/<int:experiment_id>/submitted/', views.report_submitted, name='report_submitted'),
    path('experiment/<int:experiment_id>/auto_save_report/', views.auto_save_report, name='auto_save_report'),
    path('my-reports/', views.my_evaluated_reports, name='report_list'),
    path('my-reports/<int:pk>/', views.view_report_detail, name='report_detail'),

    # path('experiment/<int:experiment_id>/submit_report/', views.submit_report, name='submit_report'),
    # path('report_submitted/<int:experiment_id>/', views.report_submitted, name='report_submitted'),
    # path('autosave-draft/<int:experiment_id>/', views.auto_save_draft, name='auto_save_draft'),


]

from django.conf import settings
from django.conf.urls.static import static

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


