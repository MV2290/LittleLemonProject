# Generated by Django 4.2.9 on 2024-02-05 13:56

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('LittleLemonAPI', '0003_alter_menuitem_featured'),
    ]

    operations = [
        migrations.RenameField(
            model_name='cart',
            old_name='menuitem',
            new_name='item',
        ),
        migrations.AlterUniqueTogether(
            name='cart',
            unique_together={('item', 'user')},
        ),
    ]
