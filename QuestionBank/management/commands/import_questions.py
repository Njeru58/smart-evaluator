#import_questions.py

import pandas as pd
from django.core.management.base import BaseCommand
from QuestionBank.models import Question


class Command(BaseCommand):
    help = 'Import questions from CSV file into the database'

    def handle(self, *args, **kwargs):
        csv_file = 'data/MEDDOGS-mod.csv'
        df = pd.read_csv(csv_file)

        for index, row in df.iterrows():
            Question.objects.create(
                question_text=row['Q'],
                option1=row['A'],
                option2=row['B'],
                option3=row['C'],
                option4=row['D'],
                correct_option=ord(row['Correct_Position']) - ord('A') + 1,
                difficulty=row['DIF [0-1]']
            )

        self.stdout.write(self.style.SUCCESS('Successfully imported questions'))
