from django.apps import AppConfig


class LeasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.leases"
    label = "leases"

    def ready(self):
        from django.db.models.signals import post_migrate

        def _resync_search_index(sender, **kwargs):
            if sender.name != self.name:
                return
            from django.core.management import call_command

            call_command("resync_search_index", verbosity=0)

        post_migrate.connect(_resync_search_index, sender=self)
