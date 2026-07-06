from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, HttpResponseForbidden
from django.utils import timezone
from .models import Story, StoryFile, Challenge, Task, TaskFile, TaskProgression, Tag, DIFFICULTY_CHOICES, DIFFICULTY_XP


def index(request):
    challenge_count = Challenge.objects.count()
    category_count = Tag.objects.count()
    active_agents = User.objects.filter(
        task_progressions__completed=True
    ).distinct().count() if Task.objects.exists() else 0

    context = {
        'challenge_count': challenge_count,
        'category_count': category_count,
        'active_agents': active_agents,
    }
    return render(request, 'main/index.html', context)


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'main/register.html', {'form': form})


# ── helpers ──────────────────────────────────────────────────────────

def _is_staff(user):
    return user.is_authenticated and user.is_staff


def _challenge_completed_tasks(challenge, user):
    """Return (completed_count, total_count) for a challenge's tasks."""
    tasks = list(challenge.tasks.all())
    if not tasks:
        return 0, 0
    done = TaskProgression.objects.filter(
        user=user, task__in=tasks, completed=True
    ).count()
    return done, len(tasks)


def _challenge_is_complete(challenge, user):
    done, total = _challenge_completed_tasks(challenge, user)
    return total > 0 and done == total


# ── public views ─────────────────────────────────────────────────────

@login_required
def story_detail(request, story_id):
    story = get_object_or_404(
        Story.objects.prefetch_related('tags', 'challenges', 'challenges__tasks', 'files'),
        id=story_id
    )

    challenges = Challenge.objects.filter(story=story).order_by('level', 'order')

    # Level-based unlocking
    levels = {}
    for c in challenges:
        levels.setdefault(c.level, []).append(c)

    unlocked_levels = {1}
    for level in sorted(levels):
        if level == 1:
            continue
        prev = levels.get(level - 1, [])
        if prev and all(_challenge_is_complete(c, request.user) for c in prev):
            unlocked_levels.add(level)
        else:
            break

    for challenge in challenges:
        challenge.is_locked = challenge.level not in unlocked_levels
        challenge.is_solved = _challenge_is_complete(challenge, request.user)
        done, total = _challenge_completed_tasks(challenge, request.user)
        challenge.tasks_done = done
        challenge.tasks_total = total

    context = {
        'story': story,
        'challenges': challenges,
    }
    return render(request, 'main/story_detail.html', context)


@login_required
def challenge_detail(request, challenge_id):
    challenge = get_object_or_404(
        Challenge.objects.select_related('story').prefetch_related(
            'tasks', 'tasks__files', 'story__tags', 'story__files'
        ),
        id=challenge_id
    )
    story = challenge.story

    # Level-based access control
    if challenge.level > 1:
        lower_challenges = Challenge.objects.filter(
            story=story, level__lt=challenge.level
        )
        lower_ids = set(lower_challenges.values_list('id', flat=True))
        completed_lower = set()
        for lc in lower_challenges:
            if _challenge_is_complete(lc, request.user):
                completed_lower.add(lc.id)
        if lower_ids and not lower_ids.issubset(completed_lower):
            return HttpResponseForbidden(
                "Complete all Level {} challenges first.".format(challenge.level - 1)
            )

    # Task data with progression & answer-format generation
    tasks_data = []
    for task in challenge.tasks.all():
        prog, _ = TaskProgression.objects.get_or_create(
            user=request.user, task=task,
            defaults={'completed': False}
        )

        # Auto-generate answer format
        answer_format = task.answer_format
        if not answer_format and task.flag.startswith("ENIGMA{") and task.flag.endswith("}"):
            inner = task.flag[7:-1]
            allowed_chars = {'.', '/', ':', '-', '_'}
            sanitized = ''.join(ch if ch in allowed_chars else 'x' for ch in inner)
            task.answer_format = sanitized
            task.save(update_fields=['answer_format'])
            answer_format = sanitized

        solved_flag = ""
        if prog.completed and task.flag.startswith("ENIGMA{") and task.flag.endswith("}"):
            solved_flag = task.flag[7:-1]

        tasks_data.append({
            'task': task,
            'progression': prog,
            'answer_format': answer_format,
            'solved_flag': solved_flag,
        })

    # ── Handle POST (reset / flag submission) ──
    result = None
    earned_xp = 0
    target_task_id = None

    if request.method == 'POST':
        if 'reset_all' in request.POST:
            TaskProgression.objects.filter(
                user=request.user, task__in=challenge.tasks.all()
            ).delete()
            return redirect('challenge_detail', challenge_id=challenge.id)

        if 'reset_task' in request.POST:
            task_id = request.POST.get('task_id')
            if task_id:
                TaskProgression.objects.filter(
                    user=request.user, task_id=task_id
                ).delete()
            return redirect('challenge_detail', challenge_id=challenge.id)

        if 'flag' in request.POST:
            task_id = request.POST.get('task_id')
            submitted_flag = request.POST.get('flag', '').strip()
            full_flag = f"ENIGMA{{{submitted_flag}}}"

            try:
                task = Task.objects.get(id=task_id, challenge=challenge)
            except Task.DoesNotExist:
                return redirect('challenge_detail', challenge_id=challenge.id)

            target_task_id = task_id
            prog = TaskProgression.objects.get_or_create(
                user=request.user, task=task,
                defaults={'completed': False}
            )[0]

            if submitted_flag and full_flag == task.flag:
                if not prog.completed:
                    prog.completed = True
                    prog.completed_at = timezone.now()
                    prog.save()
                result = 'correct'
                earned_xp = DIFFICULTY_XP.get(challenge.story.difficulty, 0)
            else:
                result = 'incorrect'

    # Refresh tasks_data after POST mutations
    for td in tasks_data:
        if td['progression'].completed:
            continue
        fresh = TaskProgression.objects.filter(
            user=request.user, task=td['task']
        ).first()
        if fresh and fresh.completed:
            td['progression'] = fresh

    tasks_done = sum(1 for td in tasks_data if td['progression'].completed)

    # Gather all task files from all challenges in this story
    story_task_files = TaskFile.objects.filter(
        task__challenge__story=story
    ).select_related('task__challenge').order_by('task__challenge__order', 'task__order', 'id')

    context = {
        'challenge': challenge,
        'story': story,
        'tasks_data': tasks_data,
        'tasks_done': tasks_done,
        'story_task_files': story_task_files,
        'result': result,
        'earned_xp': earned_xp,
        'target_task_id': target_task_id,
        'ENIGMA_PREFIX': 'ENIGMA{',
        'ENIGMA_SUFFIX': '}',
    }
    return render(request, 'main/challenge_detail.html', context)


@login_required
def download_challenge_file(request, file_id):
    task_file = get_object_or_404(TaskFile, id=file_id)
    response = HttpResponse(task_file.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{task_file.display_name}"'
    return response


@login_required
def download_story_file(request, file_id):
    story_file = get_object_or_404(StoryFile, id=file_id)
    response = HttpResponse(story_file.file.read(), content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{story_file.display_name}"'
    return response


@login_required
def dashboard(request):
    stories = Story.objects.prefetch_related('tags', 'challenges', 'challenges__tasks').all()

    solved_count = 0
    in_progress_count = 0

    for story in stories:
        all_tasks = Task.objects.filter(challenge__story=story)
        completed_ids = set(
            TaskProgression.objects.filter(
                user=request.user, task__in=all_tasks, completed=True
            ).values_list('task_id', flat=True)
        )
        started_ids = set(
            TaskProgression.objects.filter(
                user=request.user, task__in=all_tasks
            ).values_list('task_id', flat=True)
        )

        challenge_ids = set(story.challenges.values_list('id', flat=True))
        story.is_locked = False

        # A story is "solved" if every challenge in it is complete
        all_challenges_done = True
        any_started = False
        for challenge in story.challenges.all():
            tasks = list(challenge.tasks.all())
            if not tasks:
                continue
            challenge_done = all(t.id in completed_ids for t in tasks)
            challenge_started = any(t.id in started_ids for t in tasks)
            if not challenge_done:
                all_challenges_done = False
            if challenge_started:
                any_started = True

        if all_challenges_done and challenge_ids:
            story.is_solved = True
            solved_count += 1
        elif any_started:
            story.is_solved = False
            in_progress_count += 1
        else:
            story.is_solved = False

    tags = Tag.objects.all()
    tag_colors = [
        '#6366f1', '#ec4899', '#14b8a6', '#f97316', '#8b5cf6',
        '#06b6d4', '#84cc16', '#f43f5e', '#0ea5e9', '#d946ef',
    ]
    for i, tag in enumerate(tags):
        tag.color = tag_colors[i % len(tag_colors)]

    context = {
        'stories': stories,
        'solved_count': solved_count,
        'in_progress_count': in_progress_count,
        'tags': tags,
        'difficulties': DIFFICULTY_CHOICES,
    }
    return render(request, 'main/dashboard.html', context)


# ── staff-only creation / editing ────────────────────────────────────

@login_required
@user_passes_test(_is_staff)
def create_story(request):
    tags = Tag.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        difficulty = request.POST.get('difficulty', 'novice')
        tag_ids = request.POST.getlist('tags')

        if not title:
            context = {'tags': tags, 'error': 'Title is required.', 'difficulties': DIFFICULTY_CHOICES}
            return render(request, 'main/create_story.html', context)

        story = Story.objects.create(title=title, content=content, difficulty=difficulty)
        if tag_ids:
            story.tags.set(Tag.objects.filter(id__in=tag_ids))

        # Handle file uploads
        files = request.FILES.getlist('files')
        for f in files:
            StoryFile.objects.create(story=story, display_name=f.name, file=f)

        return redirect('story_detail', story_id=story.id)

    context = {'tags': tags, 'difficulties': DIFFICULTY_CHOICES}
    return render(request, 'main/create_story.html', context)


@login_required
@user_passes_test(_is_staff)
def edit_story(request, story_id):
    story = get_object_or_404(Story.objects.prefetch_related('files', 'tags'), id=story_id)
    tags = Tag.objects.all()

    if request.method == 'POST':
        if 'delete_file' in request.POST:
            file_id = request.POST.get('file_id')
            StoryFile.objects.filter(id=file_id, story=story).delete()
            return redirect('edit_story', story_id=story.id)

        story.title = request.POST.get('title', story.title).strip()
        story.content = request.POST.get('content', story.content).strip()
        story.difficulty = request.POST.get('difficulty', story.difficulty)
        tag_ids = request.POST.getlist('tags')
        if tag_ids:
            story.tags.set(Tag.objects.filter(id__in=tag_ids))
        else:
            story.tags.clear()
        story.save()

        files = request.FILES.getlist('files')
        for f in files:
            StoryFile.objects.create(story=story, display_name=f.name, file=f)

        return redirect('edit_story', story_id=story.id)

    context = {
        'story': story,
        'tags': tags,
        'difficulties': DIFFICULTY_CHOICES,
    }
    return render(request, 'main/edit_story.html', context)


@login_required
@user_passes_test(_is_staff)
def delete_story(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if request.method == 'POST':
        story.delete()
        return redirect('dashboard')
    return render(request, 'main/confirm_delete.html', {
        'object': story, 'type': 'Story', 'cancel_url': 'story_detail', 'cancel_arg': story.id
    })


@login_required
@user_passes_test(_is_staff)
def create_challenge(request, story_id):
    story = get_object_or_404(Story, id=story_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        level = request.POST.get('level', 1)
        order = request.POST.get('order', 1)

        if not title:
            context = {'story': story, 'error': 'Title is required.'}
            return render(request, 'main/create_challenge.html', context)

        challenge = Challenge.objects.create(
            story=story,
            title=title,
            description=description,
            level=level,
            order=order,
        )
        return redirect('edit_challenge', challenge_id=challenge.id)

    return render(request, 'main/create_challenge.html', {'story': story})


@login_required
@user_passes_test(_is_staff)
def edit_challenge(request, challenge_id):
    challenge = get_object_or_404(
        Challenge.objects.select_related('story').prefetch_related('tasks', 'tasks__files'),
        id=challenge_id
    )

    if request.method == 'POST':
        challenge.title = request.POST.get('title', challenge.title).strip()
        challenge.description = request.POST.get('description', challenge.description).strip()
        challenge.level = request.POST.get('level', challenge.level)
        challenge.order = request.POST.get('order', challenge.order)
        challenge.save()
        return redirect('edit_challenge', challenge_id=challenge.id)

    return render(request, 'main/edit_challenge.html', {'challenge': challenge})


@login_required
@user_passes_test(_is_staff)
def delete_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related('story'), id=challenge_id)
    story_id = challenge.story.id
    if request.method == 'POST':
        challenge.delete()
        return redirect('story_detail', story_id=story_id)
    return render(request, 'main/confirm_delete.html', {
        'object': challenge, 'type': 'Challenge', 'cancel_url': 'edit_challenge', 'cancel_arg': challenge.id
    })


@login_required
@user_passes_test(_is_staff)
def create_task(request, challenge_id):
    challenge = get_object_or_404(Challenge.objects.select_related('story'), id=challenge_id)
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        flag = request.POST.get('flag', '').strip()
        answer_format = request.POST.get('answer_format', '').strip()
        order = request.POST.get('order', 1)

        if not title:
            return render(request, 'main/create_task.html', {
                'challenge': challenge, 'error': 'Title is required.'
            })
        if not flag:
            return render(request, 'main/create_task.html', {
                'challenge': challenge, 'error': 'Flag is required.'
            })

        task = Task.objects.create(
            challenge=challenge,
            title=title,
            description=description,
            flag=flag,
            answer_format=answer_format,
            order=order,
        )

        files = request.FILES.getlist('files')
        for f in files:
            TaskFile.objects.create(task=task, display_name=f.name, file=f)

        return redirect('edit_challenge', challenge_id=challenge.id)

    return render(request, 'main/create_task.html', {'challenge': challenge})


@login_required
@user_passes_test(_is_staff)
def edit_task(request, task_id):
    task = get_object_or_404(
        Task.objects.select_related('challenge__story').prefetch_related('files'),
        id=task_id
    )
    if request.method == 'POST':
        if 'delete_file' in request.POST:
            file_id = request.POST.get('file_id')
            TaskFile.objects.filter(id=file_id, task=task).delete()
            return redirect('edit_task', task_id=task.id)

        task.title = request.POST.get('title', task.title).strip()
        task.description = request.POST.get('description', task.description).strip()
        task.flag = request.POST.get('flag', task.flag).strip()
        task.answer_format = request.POST.get('answer_format', task.answer_format).strip()
        task.order = request.POST.get('order', task.order)
        task.save()

        files = request.FILES.getlist('files')
        for f in files:
            TaskFile.objects.create(task=task, display_name=f.name, file=f)

        return redirect('edit_challenge', challenge_id=task.challenge.id)

    return render(request, 'main/edit_task.html', {'task': task})


@login_required
@user_passes_test(_is_staff)
def delete_task(request, task_id):
    task = get_object_or_404(Task.objects.select_related('challenge'), id=task_id)
    challenge_id = task.challenge.id
    if request.method == 'POST':
        task.delete()
        return redirect('edit_challenge', challenge_id=challenge_id)
    return render(request, 'main/confirm_delete.html', {
        'object': task, 'type': 'Task', 'cancel_url': 'edit_task', 'cancel_arg': task.id
    })
