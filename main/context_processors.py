from .models import TaskProgression, DIFFICULTY_XP


def xp_processor(request):
    if request.user.is_authenticated:
        completed = TaskProgression.objects.filter(
            user=request.user, completed=True
        ).select_related('task__challenge__story')
        total = 0
        for p in completed:
            total += DIFFICULTY_XP.get(p.task.challenge.story.difficulty, 0)
    else:
        total = 0
    return {'total_xp': total}
