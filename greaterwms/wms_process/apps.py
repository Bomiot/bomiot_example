from django.apps import AppConfig

ARGS_MAP = {
    'cron': ['year', 'month', 'day', 'week', 'day_of_week', 'hour', 'minute', 'second', 'start_date', 'end_date', 'timezone'],
    'interval': ['weeks', 'days', 'hours', 'minutes', 'seconds', 'start_date', 'end_date', 'timezone'],
    'date': ['run_date', 'timezone']
}

class Wms_processConfig(AppConfig):
    name = 'greaterwms.wms_process'

    def ready(self):
        from bomiot.server.core.signal import bomiot_signals, bomiot_data_signals
        from bomiot.server.core.models import JobList
        import json

        try:
            JobList.objects.get_or_create(
                job_id='example_job',
                defaults={
                    'module_name': 'greaterwms.task',
                    'func_name': 'example_job',
                    'trigger': 'interval',
                    'configuration': json.dumps({'minutes': 1}),
                    'description': 'Example scheduled task - Executed once every 1 minute',
                    'type': True,
                }
            )
        except:
            pass
