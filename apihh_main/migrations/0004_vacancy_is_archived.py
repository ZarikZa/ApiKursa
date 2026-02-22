from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apihh_main', '0003_passwordresetcode'),
    ]

    operations = [
        migrations.AddField(
            model_name='vacancy',
            name='is_archived',
            field=models.BooleanField(default=False),
        ),
    ]
