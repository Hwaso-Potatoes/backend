from django.db import migrations, models
from django.db.models import F


def fill_recorded_at(apps, schema_editor):
    WalkingPath = apps.get_model('walk', 'WalkingPath')
    WalkingPath.objects.filter(recorded_at__isnull=True).update(recorded_at=F('timestamp'))


class Migration(migrations.Migration):

    dependencies = [
        ('walk', '0003_walkpreference'),
    ]

    operations = [
        migrations.AddField(
            model_name='walkingpath',
            name='recorded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(fill_recorded_at, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name='walkingpath',
            options={'ordering': ['recorded_at', 'id']},
        ),
        migrations.AddIndex(
            model_name='walkingpath',
            index=models.Index(fields=['session', 'recorded_at'], name='walkpath_session_recorded_idx'),
        ),
    ]