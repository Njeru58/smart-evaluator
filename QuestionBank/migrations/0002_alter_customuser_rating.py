# Generated by Django 5.0 on 2024-05-18 02:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('QuestionBank', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='rating',
            field=models.FloatField(default=5.0),
        ),
    ]
