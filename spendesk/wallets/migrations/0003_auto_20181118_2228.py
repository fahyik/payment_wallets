# Generated by Django 2.0.9 on 2018-11-18 22:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallets', '0002_auto_20181118_2209'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='wallet',
            unique_together=set(),
        ),
        migrations.AddIndex(
            model_name='wallet',
            index=models.Index(fields=['currency', 'is_master'], name='wallets_wal_currenc_ee9b4b_idx'),
        ),
    ]
