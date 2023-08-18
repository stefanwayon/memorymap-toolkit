# Generated by Django 3.2.18 on 2023-08-09 16:25

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('mmt_map', '0033_auto_20230809_1625'),
    ]

    operations = [
        migrations.AlterField(
            model_name='line',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='point',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.AlterField(
            model_name='polygon',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
