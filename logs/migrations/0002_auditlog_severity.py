from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("logs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="severity",
            field=models.CharField(choices=[("info", "Info"), ("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="info", max_length=10),
        ),
    ]
