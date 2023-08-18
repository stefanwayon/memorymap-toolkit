# Generated by Django 3.2.18 on 2023-08-09 15:19

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('mmt_map', '0031_auto_20230109_1535'),
    ]

    operations = [
        migrations.AddField(
            model_name='line',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='point',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.AddField(
            model_name='polygon',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
    ]
