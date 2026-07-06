from django.contrib import admin
from .models import Tag, Story, StoryFile, Challenge, Task, TaskFile, TaskProgression


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


class StoryFileInline(admin.TabularInline):
    model = StoryFile
    extra = 0


@admin.register(Story)
class StoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'difficulty', 'challenge_count', 'created_at')
    search_fields = ('title', 'content')
    list_filter = ('difficulty', 'tags')
    inlines = [StoryFileInline]

    def challenge_count(self, obj):
        return obj.challenges.count()
    challenge_count.short_description = 'Challenges'


class TaskFileInline(admin.TabularInline):
    model = TaskFile
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'challenge', 'order', 'answer_format', 'created_at')
    list_filter = ('challenge__story',)
    search_fields = ('title', 'description', 'answer_format')
    ordering = ('challenge__story', 'challenge', 'order')
    inlines = [TaskFileInline]


@admin.register(TaskProgression)
class TaskProgressionAdmin(admin.ModelAdmin):
    list_display = ('user', 'task', 'completed', 'started_at', 'completed_at')
    list_filter = ('completed',)
    search_fields = ('user__username', 'task__title')


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'story', 'level', 'order', 'created_at')
    list_filter = ('level', 'story')
    search_fields = ('title', 'description')
    ordering = ('story', 'level', 'order')


@admin.register(StoryFile)
class StoryFileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'story', 'uploaded_at')
    search_fields = ('display_name',)


@admin.register(TaskFile)
class TaskFileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'task', 'uploaded_at')
    search_fields = ('display_name',)
