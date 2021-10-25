# serializers.py
# from rest_framework import serializers

# from .models import AppItem, AppTracker, AppTrackerChange


# class AppSiteSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = AppSite
#         fields = ("url", "monitor_path", "created_at", "updated_at")


# class AppTrackerSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = AppTracker
#         fields = ("site_id", "url", "monitor_path", "type", "created_at", "updated_at")


# class AppTrackerChangeSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = AppTrackerChange
#         fields = ("page", "content", "is_available", "created_at")
