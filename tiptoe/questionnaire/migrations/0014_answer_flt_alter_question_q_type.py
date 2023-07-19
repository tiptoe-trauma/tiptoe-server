# Generated by Django 4.1.7 on 2023-07-11 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaire", "0013_alter_question_q_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="answer",
            name="flt",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="question",
            name="q_type",
            field=models.CharField(
                choices=[
                    ("combo", "Combo Box"),
                    ("check", "Check Boxes"),
                    ("text", "Text Field"),
                    ("int", "Integer Field"),
                    ("unit", "Unit Int Field"),
                    ("flt", "Float Field"),
                    ("bool", "Yes or No"),
                ],
                max_length=5,
            ),
        ),
    ]
