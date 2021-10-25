from django.db import models
from django_q.tasks import schedule
from django_q.models import Schedule
import json

# pre-save and delete signals
from django.db.models.signals import pre_save, post_save, pre_delete

# schedule, created = IntervalSchedule.objects.get_or_create(
#     every=60,
#     period=IntervalSchedule.SECONDS,
# )


class AppBrand(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_brands"


class AppCategory(models.Model):
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_categories"


class AppItem(models.Model):
    product = models.ForeignKey("AppProduct", models.DO_NOTHING)
    store = models.ForeignKey("AppStore", models.DO_NOTHING)
    url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_items"


class AppProduct(models.Model):
    category = models.ForeignKey(AppCategory, models.DO_NOTHING)
    brand = models.ForeignKey(AppBrand, models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_products"


class AppStoreLocation(models.Model):
    store = models.ForeignKey("AppStore", models.DO_NOTHING)
    name = models.CharField(max_length=255)
    full_address = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_store_locations"


class AppStore(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    url = models.TextField()
    country = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_stores"


class AppTrackerChange(models.Model):
    tracker = models.ForeignKey("AppTracker", models.DO_NOTHING)
    change = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_tracker_changes"


class AppTracker(models.Model):
    item = models.ForeignKey(AppItem, models.DO_NOTHING)
    location = models.ForeignKey(
        AppStoreLocation, models.DO_NOTHING, blank=True, null=True
    )
    active = models.BooleanField()
    frequency = models.IntegerField()
    type = models.CharField(max_length=255)
    method = models.CharField(max_length=255)
    params = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_trackers"


def create_task(sender, instance, **kwargs):
    url = instance.site.url + instance.url
    if not Schedule.objects.filter(name=instance.page_id).exists():
        schedule(
            "api.tasks.check_page",
            instance.page_id,
            url,
            instance.site.monitor_path,
            instance.site.available_tag,
            name=instance.tracker_id,
            schedule_type=Schedule.MINUTES,
            minutes=1,
            repeats=-1,
        )
    else:
        task = Schedule.objects.get(name=instance.tracker_id)
        args = [
            instance.page_id,
            url,
            instance.site.monitor_path,
            instance.site.available_tag,
        ]
        args = ",".join(f"'{a}'" for a in args)
        task.args = args
        task.save()


def delete_task(sender, instance, **kwargs):
    task = Schedule.objects.get(name=instance.page_id)
    task.delete()


post_save.connect(create_task, sender=AppTracker)
pre_delete.connect(delete_task, sender=AppTracker)


class AppUserProfile(models.Model):
    uid = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    phone = models.CharField(max_length=255)
    comments = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_user_profiles"


class AppUserSubscription(models.Model):
    user = models.ForeignKey(AppUserProfile, models.DO_NOTHING)
    item = models.ForeignKey(AppItem, models.DO_NOTHING, blank=True, null=True)
    product = models.ForeignKey(AppProduct, models.DO_NOTHING, blank=True, null=True)
    paused = models.BooleanField()
    type = models.CharField(max_length=255)
    target_price = models.DecimalField(
        max_digits=65535, decimal_places=65535, blank=True, null=True
    )

    class Meta:
        managed = False
        db_table = "app_user_subscriptions"


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = "auth_group"


class AuthGroupPermissions(models.Model):
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey("AuthPermission", models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_group_permissions"
        unique_together = (("group", "permission"),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey("DjangoContentType", models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "auth_permission"
        unique_together = (("content_type", "codename"),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "auth_user"


class AuthUserGroups(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_user_groups"
        unique_together = (("user", "group"),)


class AuthUserUserPermissions(models.Model):
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "auth_user_user_permissions"
        unique_together = (("user", "permission"),)


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey(
        "DjangoContentType", models.DO_NOTHING, blank=True, null=True
    )
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = "django_admin_log"


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "django_content_type"
        unique_together = (("app_label", "model"),)


class DjangoMigrations(models.Model):
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "django_migrations"


class DjangoQOrmq(models.Model):
    key = models.CharField(max_length=100)
    payload = models.TextField()
    lock = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "django_q_ormq"


class DjangoQSchedule(models.Model):
    func = models.CharField(max_length=256)
    hook = models.CharField(max_length=256, blank=True, null=True)
    args = models.TextField(blank=True, null=True)
    kwargs = models.TextField(blank=True, null=True)
    schedule_type = models.CharField(max_length=1)
    repeats = models.IntegerField()
    next_run = models.DateTimeField(blank=True, null=True)
    task = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    minutes = models.SmallIntegerField(blank=True, null=True)
    cron = models.CharField(max_length=100, blank=True, null=True)
    cluster = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "django_q_schedule"


class DjangoQTask(models.Model):
    name = models.CharField(max_length=100)
    func = models.CharField(max_length=256)
    hook = models.CharField(max_length=256, blank=True, null=True)
    args = models.TextField(blank=True, null=True)
    kwargs = models.TextField(blank=True, null=True)
    result = models.TextField(blank=True, null=True)
    started = models.DateTimeField()
    stopped = models.DateTimeField()
    success = models.BooleanField()
    id = models.CharField(primary_key=True, max_length=32)
    group = models.CharField(max_length=100, blank=True, null=True)
    attempt_count = models.IntegerField()

    class Meta:
        managed = False
        db_table = "django_q_task"


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "django_session"
