from django.db import migrations


def forward(apps, schema_editor):
    Challenge = apps.get_model('main', 'Challenge')
    ChallengeFile = apps.get_model('main', 'ChallengeFile')
    UserProgression = apps.get_model('main', 'UserProgression')
    Task = apps.get_model('main', 'Task')
    TaskFile = apps.get_model('main', 'TaskFile')
    TaskProgression = apps.get_model('main', 'TaskProgression')

    for challenge in Challenge.objects.all():
        task = Task.objects.create(
            challenge=challenge,
            title=challenge.title,
            description=challenge.description,
            flag=challenge.flag if challenge.flag else 'ENIGMA{placeholder}',
            answer_format=challenge.answer_format,
            order=1,
        )

        for cf in ChallengeFile.objects.filter(challenge=challenge):
            TaskFile.objects.create(
                task=task,
                display_name=cf.display_name,
                file=cf.file,
            )

        for up in UserProgression.objects.filter(challenge=challenge):
            TaskProgression.objects.create(
                user=up.user,
                task=task,
                completed=up.completed,
                completed_at=up.completed_at,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0007_alter_challenge_answer_format_and_more"),
    ]

    operations = [
        migrations.RunPython(forward, migrations.RunPython.noop),
    ]
