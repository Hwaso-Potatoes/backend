from django.core.management.base import BaseCommand

from walk.geo import classify_walk


class Command(BaseCommand):
    help = "산책 위치 유형(숲/도시/새로운 지역)을 판정합니다. 예: python manage.py classify_walk 3"

    def add_arguments(self, parser):
        parser.add_argument('walk_id', type=int)
        parser.add_argument('--force', action='store_true', help='이미 판정된 산책도 숲/도시를 다시 판정')

    def handle(self, *args, **options):
        result = classify_walk(options['walk_id'], force=options['force'])
        self.stdout.write(self.style.SUCCESS(f"walk {options['walk_id']}: {result}"))
