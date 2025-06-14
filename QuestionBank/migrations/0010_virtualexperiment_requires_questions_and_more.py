# Generated by Django 5.1.5 on 2025-06-09 06:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionBank', '0009_experimentquestion'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualexperiment',
            name='requires_questions',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='virtualexperiment',
            name='requires_report',
            field=models.BooleanField(default=True),
        ),
    ]
