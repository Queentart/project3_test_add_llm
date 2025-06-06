# Generated by Django 5.2.1 on 2025-05-28 02:26

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("image_generator", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "session_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        unique=True,
                        verbose_name="세션 ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="생성 날짜"),
                ),
            ],
            options={
                "verbose_name": "대화",
                "verbose_name_plural": "대화들",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "sender",
                    models.CharField(
                        choices=[("user", "사용자"), ("ai", "AI")],
                        max_length=10,
                        verbose_name="발신자",
                    ),
                ),
                ("text", models.TextField(verbose_name="내용")),
                (
                    "timestamp",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="시간"
                    ),
                ),
                (
                    "image_url",
                    models.URLField(
                        blank=True, max_length=500, null=True, verbose_name="이미지 URL"
                    ),
                ),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="messages",
                        to="image_generator.conversation",
                        verbose_name="대화",
                    ),
                ),
            ],
            options={
                "verbose_name": "메시지",
                "verbose_name_plural": "메시지들",
                "ordering": ["timestamp"],
            },
        ),
    ]
