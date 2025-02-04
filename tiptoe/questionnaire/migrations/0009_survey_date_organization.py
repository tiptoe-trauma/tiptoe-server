# Generated by Django 4.1.7 on 2023-03-13 18:24

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("questionnaire", "0008_rename_activeorganization_activesurvey"),
    ]

    operations = [
        migrations.AddField(
            model_name="survey",
            name="date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(blank=True, max_length=200)),
                ("org_type", models.CharField(blank=True, max_length=6)),
                (
                    "users",
                    models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
                ),
            ],
        ),
    ]
