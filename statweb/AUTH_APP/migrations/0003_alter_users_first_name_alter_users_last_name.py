# Generated by Django 5.0.4 on 2024-11-12 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('AUTH_APP', '0002_remove_users_excel_file_userexcelfile'),
    ]

    operations = [
        migrations.AlterField(
            model_name='users',
            name='first_name',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='last_name',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]
