from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('lesson', '0002_alter_lessoncontent_type'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='lesson',
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name='lesson',
            name='slug',
            field=models.SlugField(blank=True, max_length=255, null=True),
        ),
    ]
