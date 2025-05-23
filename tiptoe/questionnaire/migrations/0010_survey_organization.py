# Generated by Django 4.1.7 on 2023-03-14 19:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaire", "0009_survey_date_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="surveys",
                to="questionnaire.organization",
            ),
        ),
    ]
