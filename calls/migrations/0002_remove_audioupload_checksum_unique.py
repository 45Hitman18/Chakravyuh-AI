from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('calls', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='audioupload',
            name='checksum',
            field=models.CharField(max_length=128),
        ),
    ]