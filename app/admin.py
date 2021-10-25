from django.contrib import admin
from django_q import models as q_models
from django_q import admin as q_admin

from .models import (
    AppStore,
    AppProduct,
    AppBrand,
    AppCategory,
    AppItem,
    AppTracker,
    AppTrackerChange,
    AppUserProfile,
    AppUserSubscription,
)

admin.site.register(AppStore)
admin.site.register(AppProduct)
admin.site.register(AppBrand)
admin.site.register(AppCategory)
admin.site.register(AppItem)
admin.site.register(AppTracker)
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
