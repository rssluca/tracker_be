import pprint
from cron_converter import Cron
from django.db import models
from django_countries.fields import CountryField
from django.core.exceptions import ValidationError
from django_q.tasks import schedule
from django_q.models import Schedule
from .constants import TRACKER_TYPES, TRACKER_METHODS, DEFAULT_PARAMS

pp = pprint.PrettyPrinter(indent=4)

# pre-save and delete signals
from django.db.models.signals import pre_save, post_save, pre_delete


def get_default_params():
    return DEFAULT_PARAMS


class AppBrand(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_brands"

    def __str__(self):
        return self.name


class AppCategory(models.Model):
    parent = models.ForeignKey("self", models.DO_NOTHING, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_categories"
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


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

    def __str__(self):
        return self.brand.name + " " + self.name


class AppStoreLocation(models.Model):
    site = models.ForeignKey("AppSite", models.DO_NOTHING)
    name = models.CharField(max_length=255)
    full_address = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_store_locations"

    def __str__(self):
        return self.name


class AppSite(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    url = models.TextField()
    country = CountryField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_sites"

    def __str__(self):
        return self.name


class AppTrackerChange(models.Model):
    tracker = models.ForeignKey("AppTracker", models.CASCADE)
    item_desc = models.CharField(max_length=255)
    item_url = models.CharField(max_length=255)
    available = models.BooleanField()
    price = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_tracker_changes"

    def __str__(self):
        return self.tracker.site.name + " " + self.tracker.name


class AppTracker(models.Model):
    name = models.CharField(max_length=255)
    search_key = models.CharField(max_length=255, blank=True, null=True)
    url = models.TextField()
    site = models.ForeignKey(AppSite, models.DO_NOTHING)
    product = models.ForeignKey(AppProduct, models.DO_NOTHING, blank=True, null=True)
    location = models.ForeignKey(
        AppStoreLocation, models.DO_NOTHING, blank=True, null=True
    )
    active = models.BooleanField(default=True)
    frequency = models.IntegerField(default=1)
    repeats = models.IntegerField(default=-1)
    cron_schedule = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="https://docs.oracle.com/cd/E12058_01/doc/doc.1014/e12030/cron_expressions.htm",
    )
    type = models.CharField(
        max_length=255,
        choices=[(t, t) for t in TRACKER_TYPES],
        default="new_item",
    )
    method = models.CharField(
        max_length=255,
        choices=[(t, t) for t in TRACKER_METHODS],
        default="xpath",
    )
    params = models.JSONField(default=get_default_params)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "app_trackers"

    def clean(self):
        # Check id cron is valid
        try:
            cron_instance = Cron(self.cron_schedule)
        except:
            raise ValidationError("Cron schedule format is invalid.")

    def __str__(self):
        return self.site.name + " " + self.name


def create_task(sender, instance, **kwargs):
    params = [
        instance.id,
        instance.name,
        instance.search_key,
        instance.site.id,
        instance.url,
        instance.type,
        instance.method,
        instance.params,
    ]

    if instance.cron_schedule:
        sched_params = {
            "schedule_type": Schedule.CRON,
            "cron": instance.cron_schedule,
        }
    else:
        sched_params = {
            "schedule_type": Schedule.MINUTES,
            "minutes": instance.frequency,
            "repeats": instance.repeats,
        }

    if not Schedule.objects.filter(name=instance.id).exists():
        if instance.active:
            schedule(
                "app.utils.tracker.check_" + instance.type,
                *params,
                hook="app.hooks.notify_error",
                name=instance.id,
                **sched_params
            )
    else:
        task = Schedule.objects.get(name=instance.id)
        if instance.active:
            task.args = tuple(params)
            if instance.cron_schedule:
                task.schedule_type = Schedule.CRON
                task.cron = instance.cron
            else:
                task.schedule_type = Schedule.MINUTES
                task.minutes = instance.frequency
                task.repeats = instance.repeats
            task.save()
        else:
            # delete task from the queue if deactivated
            task.delete()


def delete_task(sender, instance, **kwargs):
    try:
        task = Schedule.objects.get(name=instance.id)
        task.delete()
    except:
        # NOTE add notification/logging
        pass


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


# User can be subscribe to a generic item (product) or to a specific tracker
class AppUserSubscription(models.Model):
    user = models.ForeignKey(AppUserProfile, models.DO_NOTHING)
    tracker = models.ForeignKey(AppTracker, models.DO_NOTHING, blank=True, null=True)
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
