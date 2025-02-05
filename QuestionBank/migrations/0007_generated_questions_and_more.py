# Generated by Django 5.0.6 on 2024-06-11 06:46

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionBank', '0006_evaluatorai'),
    ]

    operations = [
        migrations.CreateModel(
            name='generated_questions',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('topic', models.CharField(max_length=100)),
                ('number_of_questions', models.IntegerField()),
                ('prompt_instructions', models.TextField()),
                ('generated_questions', models.TextField()),
            ],
        ),
        migrations.AlterField(
            model_name='evaluatorai',
            name='generated_questions',
            field=models.TextField(blank=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
