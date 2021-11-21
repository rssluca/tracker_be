from django.contrib import admin
from django.db import models

# https://github.com/jmrivas86/django-json-widget
from django_json_widget.widgets import JSONEditorWidget
from django_q import models as q_models
from django_q import admin as q_admin

from .models import (
    AppSite,
    AppProduct,
    AppBrand,
    AppCategory,
    AppTracker,
    AppTrackerChange,
    AppUserProfile,
    AppUserSubscription,
)


# class AppItemAdmin(admin.ModelAdmin):
#     formfield_overrides = {
#         models.CharField: {"widget": TextInput(attrs={"size": "80"})},
#     }


@admin.register(AppTracker)
class AppTrackerAdmin(admin.ModelAdmin):
    formfield_overrides = {
        # fields.JSONField: {'widget': JSONEditorWidget}, # if django < 3.1
        models.JSONField: {"widget": JSONEditorWidget},
    }
    save_as = True


admin.site.register(AppSite)
admin.site.register(AppProduct)
admin.site.register(AppBrand)
admin.site.register(AppCategory)
# admin.site.register(AppItem, AppItemAdmin)
admin.site.register(AppTrackerChange)
admin.site.register(AppUserProfile)
admin.site.register(AppUserSubscription)

admin.site.unregister([q_models.Failure])


@admin.register(q_models.Failure)
class ChildClassAdmin(q_admin.FailAdmin):
    list_display = (
        "name",
        "func",
        "result",
        "started",
        # add attempt_count to list_display
        "attempt_count",
    )
