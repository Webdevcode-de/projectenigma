from django.db import models
from django.conf import settings


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


DIFFICULTY_CHOICES = [
    ('novice', 'Novice'),
    ('script-kiddie', 'Script-Kiddie'),
    ('analyst', 'Analyst'),
    ('operator', 'Operator'),
    ('cyber-spy', 'Cyber-Spy'),
    ('infiltrator', 'Infiltrator'),
    ('elite-hacker', 'Elite Hacker'),
    ('enigma-master', 'Enigma Master'),
]

DIFFICULTY_XP = {
    'novice': 10,
    'script-kiddie': 25,
    'analyst': 50,
    'operator': 100,
    'cyber-spy': 200,
    'infiltrator': 350,
    'elite-hacker': 500,
    'enigma-master': 1000,
}


class Story(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='novice')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, related_name='stories', blank=True)

    def __str__(self):
        return self.title


class StoryFile(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='files')
    display_name = models.CharField(max_length=100)
    file = models.FileField(upload_to='challenge_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.story.title} - {self.display_name}"


class Challenge(models.Model):
    story = models.ForeignKey(Story, on_delete=models.CASCADE, related_name='challenges')
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    order = models.PositiveIntegerField(default=1)
    level = models.PositiveIntegerField(default=1, help_text="Challenges at the same level can be done in any order. Complete all challenges at level N to unlock level N+1.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.story.title} - Lvl {self.order}: {self.title}"


class Task(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=100)
    description = models.TextField()
    flag = models.CharField(max_length=255)
    answer_format = models.CharField(max_length=255, blank=True, help_text="Shows the expected answer format. Leave blank to auto-generate from the flag.")
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.challenge.title} - Task {self.order}: {self.title}"


class TaskFile(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='files')
    display_name = models.CharField(max_length=100)
    file = models.FileField(upload_to='challenge_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.task.title} - {self.display_name}"


class TaskProgression(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_progressions')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='user_progressions')
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'task')

    def __str__(self):
        status = "Completed" if self.completed else "In Progress"
        return f"{self.user.username} - {self.task.title} ({status})"


