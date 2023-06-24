from celery import Celery

celery_app = Celery('my_app', broker='amqp://rabbitmq:5672//')

@celery_app.task
def run_ffmpeg(cmd):
    os.system(cmd)
