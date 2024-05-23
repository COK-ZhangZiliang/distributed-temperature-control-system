# Generated by Django 4.1 on 2024-05-21 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("air_condition", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="room", old_name="wind_speed", new_name="fan_speed",
        ),
        migrations.AlterField(
            model_name="room",
            name="room_id",
            field=models.IntegerField(default=0, verbose_name="房间号"),
        ),
    ]
